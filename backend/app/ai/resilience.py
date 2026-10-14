"""
Resilience helpers for the Gemini free tier.

The free tier fails in a few typical ways:
- 429 RESOURCE_EXHAUSTED: requests per minute / per day quota of a model is used up
- 503 UNAVAILABLE: "The model is overloaded", very common on gemini-2.5-flash
- empty answers: the model finishes with no text and no tool call

This module retries a little, then falls back to other Gemini models (each model
has its own free tier quota), throttles requests on our side, and turns provider
errors into messages a user can act on.
"""

import asyncio
import logging
import re
import time
import warnings
from collections.abc import AsyncIterator, Iterator
from typing import Any

import httpx
from langchain_core.callbacks import AsyncCallbackManagerForLLMRun
from langchain_core.exceptions import (
    ModelAPIError,
    ModelAuthenticationError,
    ModelNotFoundError,
    ModelPermissionDeniedError,
    ModelRateLimitError,
)
from langchain_core.messages import AIMessage, BaseMessage
from langchain_core.outputs import ChatGenerationChunk, ChatResult
from langchain_core.rate_limiters import InMemoryRateLimiter
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.errors import GraphRecursionError
from pydantic import Field

from core.config import settings

logger = logging.getLogger(__name__)

# Newer Gemini models ignore `temperature`; the SDK warns on every call
warnings.filterwarnings("ignore", message=".*uses fixed sampling defaults.*")

# Errors after which another model may succeed
_FALLBACK_ERRORS = (
    ModelRateLimitError,
    ModelAPIError,
    ModelNotFoundError,
    ModelPermissionDeniedError,
    TimeoutError,
    asyncio.TimeoutError,
    httpx.TimeoutException,
)

# model name -> time.monotonic() until which the model is skipped
_model_cooldown_until: dict[str, float] = {}


# Gemini tells how long to wait, e.g. "Please retry in 40m10.08s." or "retryDelay": "34s"
_RETRY_IN_RE = re.compile(r"retry in (?:(\d+)h)?(?:(\d+)m)?(?:([\d.]+)s)?", re.IGNORECASE)
_RETRY_DELAY_RE = re.compile(r"retryDelay['\"]?\s*:\s*['\"]([\d.]+)s")


def _suggested_retry_seconds(error: Exception) -> float | None:
    text = str(error)
    if match := _RETRY_IN_RE.search(text):
        hours, minutes, seconds = (float(g) if g else 0.0 for g in match.groups())
        total = hours * 3600 + minutes * 60 + seconds
        if total > 0:
            return total
    if match := _RETRY_DELAY_RE.search(text):
        return float(match.group(1))
    return None


def _cooldown_seconds(error: Exception) -> float:
    """How long a failing model is skipped, so every request doesn't pay its retry delay again."""
    if isinstance(error, (ModelNotFoundError, ModelPermissionDeniedError)):
        return 3600
    if isinstance(error, ModelRateLimitError):
        # Daily free tier quotas say "retry in 40m", per minute quotas a few seconds
        return min(max(_suggested_retry_seconds(error) or 60, 10), 3600)
    return 15


EMPTY_RESPONSE_MESSAGE = (
    "Sorry, I could not generate an answer this time (the model returned an empty response). "
    "Please try again or rephrase your question."
)


def message_text(content: str | list[str | dict]) -> str:
    """Plain text of a message content, ignoring non text blocks."""
    if isinstance(content, str):
        return content
    return "".join(
        item if isinstance(item, str) else item.get("text", "")
        for item in content
        if isinstance(item, str) or item.get("type") == "text"
    )


def is_empty_ai_message(message: BaseMessage) -> bool:
    """True when the model answered with neither text nor a tool call."""
    return (
        isinstance(message, AIMessage)
        and not message.tool_calls
        and not message_text(message.content).strip()
    )


def build_rate_limiter() -> InMemoryRateLimiter | None:
    """Token bucket shared by every Gemini call of this process."""
    if settings.GEMINI_REQUESTS_PER_MINUTE <= 0:
        return None
    return InMemoryRateLimiter(
        requests_per_second=settings.GEMINI_REQUESTS_PER_MINUTE / 60,
        check_every_n_seconds=0.1,
        max_bucket_size=2,
    )


class ResilientChatGoogleGenerativeAI(ChatGoogleGenerativeAI):
    """
    Gemini chat model that falls back to the next model in `fallback_models`
    when the current one is rate limited, overloaded or unavailable.

    It stays a ChatGoogleGenerativeAI, so bind_tools(), LangGraph agents and the
    supervisor work exactly as before.
    """

    fallback_models: list[str] = Field(default_factory=list)

    def _candidates(self) -> Iterator["ResilientChatGoogleGenerativeAI"]:
        names = [self.model, *[name for name in self.fallback_models if name != self.model]]
        now = time.monotonic()
        ready = [name for name in names if _model_cooldown_until.get(name, 0) <= now]
        # If every model is cooling down, still try them all rather than failing without a call
        for name in ready or names:
            yield self if name == self.model else self.model_copy(update={"model": name, "fallback_models": []})

    @staticmethod
    def _on_model_failed(model: str, error: Exception) -> None:
        cooldown = _cooldown_seconds(error)
        _model_cooldown_until[model] = time.monotonic() + cooldown
        logger.warning(f"Gemini model '{model}' failed, skipping it for {cooldown:.0f}s and trying the next model: {error}")

    async def _agenerate(
        self,
        messages: list[BaseMessage],
        stop: list[str] | None = None,
        run_manager: AsyncCallbackManagerForLLMRun | None = None,
        **kwargs: Any,
    ) -> ChatResult:
        last_error: Exception | None = None
        for candidate in self._candidates():
            try:
                return await super(ResilientChatGoogleGenerativeAI, candidate)._agenerate(
                    messages, stop, run_manager, **kwargs
                )
            except _FALLBACK_ERRORS as e:
                self._on_model_failed(candidate.model, e)
                last_error = e
        raise last_error

    async def _astream(
        self,
        messages: list[BaseMessage],
        stop: list[str] | None = None,
        run_manager: AsyncCallbackManagerForLLMRun | None = None,
        **kwargs: Any,
    ) -> AsyncIterator[ChatGenerationChunk]:
        last_error: Exception | None = None
        for candidate in self._candidates():
            started = False
            try:
                async for chunk in super(ResilientChatGoogleGenerativeAI, candidate)._astream(
                    messages, stop, run_manager, **kwargs
                ):
                    started = True
                    yield chunk
                return
            except _FALLBACK_ERRORS as e:
                # Once tokens reached the user we can't switch models without mixing answers
                if started:
                    raise
                self._on_model_failed(candidate.model, e)
                last_error = e
        raise last_error


def user_facing_error(error: BaseException) -> str:
    """Translate a provider / graph error into a message that is safe to show to users."""
    if isinstance(error, ModelRateLimitError):
        return (
            "The AI model is receiving too many requests (Gemini free tier quota reached). "
            "Please wait about a minute and try again."
        )
    if isinstance(error, ModelAPIError):
        return "The AI model is temporarily overloaded. Please try again in a few seconds."
    if isinstance(error, (ModelAuthenticationError, ModelPermissionDeniedError)):
        return "The AI model rejected the request. Please check the GOOGLE_API_KEY configuration."
    if isinstance(error, ModelNotFoundError):
        return "The configured AI model was not found. Please check DEFAULT_MODEL / GEMINI_FALLBACK_MODELS."
    if isinstance(error, (TimeoutError, asyncio.TimeoutError, httpx.TimeoutException)):
        return "The AI model took too long to answer. Please try again."
    if isinstance(error, GraphRecursionError):
        return "The assistant needed too many steps to answer this question. Please make it more specific."
    return "Something went wrong while generating the answer. Please try again."
