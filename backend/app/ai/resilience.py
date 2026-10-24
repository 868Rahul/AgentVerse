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
from collections.abc import AsyncIterator
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
    limiter = InMemoryRateLimiter(
        requests_per_second=settings.GEMINI_REQUESTS_PER_MINUTE / 60,
        check_every_n_seconds=0.05,
        max_bucket_size=settings.GEMINI_BURST_REQUESTS,
    )
    # The bucket starts empty, which made even the first question wait ~6 s. Start it full instead:
    # a normal question (2-4 model calls) then never waits, only sustained bursts are slowed down.
    limiter.available_tokens = float(settings.GEMINI_BURST_REQUESTS)
    return limiter


class ResilientChatGoogleGenerativeAI(ChatGoogleGenerativeAI):
    """
    Gemini chat model that falls back to the next model in `fallback_models`
    when the current one is rate limited, overloaded or unavailable.

    It stays a ChatGoogleGenerativeAI, so bind_tools(), LangGraph agents and the
    supervisor work exactly as before.
    """

    fallback_models: list[str] = Field(default_factory=list)
    # Free tier requests sometimes sit in Google's queue for 10-30 s. If the model has not started
    # answering after this many seconds, the same request is also sent to the next model and the
    # first one to answer wins (a "hedged" request). None disables it.
    hedge_after_seconds: float | None = None

    def _candidates(self) -> list["ResilientChatGoogleGenerativeAI"]:
        names = [self.model, *[name for name in self.fallback_models if name != self.model]]
        now = time.monotonic()
        ready = [name for name in names if _model_cooldown_until.get(name, 0) <= now]
        # If every model is cooling down, still try them all rather than failing without a call
        return [
            self if name == self.model
            else self.model_copy(update={"model": name, "fallback_models": [], **thinking_settings(name)})
            for name in ready or names
        ]

    @staticmethod
    def _on_model_failed(model: str, error: Exception) -> None:
        cooldown = _cooldown_seconds(error)
        _model_cooldown_until[model] = time.monotonic() + cooldown
        logger.warning(f"Gemini model '{model}' failed, skipping it for {cooldown:.0f}s and trying the next model: {error}")

    async def _race(self, start_attempt):
        """
        Run attempts on the candidate models: the next model is started when the current one fails
        with a fallback error, or (hedging) when it is still silent after `hedge_after_seconds`.
        `start_attempt(candidate)` returns an awaitable that resolves to the attempt's first result.
        Returns (candidate, result, cleanup) of the winner; the losers are cancelled.
        """
        candidates = iter(self._candidates())
        running: dict[asyncio.Task, tuple] = {}
        last_error: Exception | None = None

        def start_next() -> bool:
            candidate = next(candidates, None)
            if candidate is None:
                return False
            awaitable, cleanup = start_attempt(candidate)
            running[asyncio.ensure_future(awaitable)] = (candidate, cleanup)
            return True

        async def cancel(task):
            candidate, cleanup = running.pop(task)
            task.cancel()
            await asyncio.gather(task, return_exceptions=True)
            await cleanup()

        start_next()
        try:
            while running:
                # hedge only while a single attempt is running, so at most two requests are in flight
                timeout = self.hedge_after_seconds if len(running) == 1 else None
                done, _ = await asyncio.wait(running, timeout=timeout, return_when=asyncio.FIRST_COMPLETED)
                if not done:
                    slow = next(iter(running.values()))[0].model
                    if start_next():
                        logger.info(f"Gemini model '{slow}' is slow, also asking the next model (hedged request)")
                    else:
                        # no other model left: just keep waiting for the running one
                        done, _ = await asyncio.wait(running, return_when=asyncio.FIRST_COMPLETED)
                for task in done:
                    candidate, cleanup = running.pop(task)
                    error = task.exception()
                    if error is None:
                        return candidate, task.result(), cleanup
                    await cleanup()
                    if not isinstance(error, _FALLBACK_ERRORS):
                        raise error
                    self._on_model_failed(candidate.model, error)
                    last_error = error
                if not running and not start_next():
                    break
        finally:
            for task in list(running):
                await cancel(task)
        raise last_error

    async def _agenerate(
        self,
        messages: list[BaseMessage],
        stop: list[str] | None = None,
        run_manager: AsyncCallbackManagerForLLMRun | None = None,
        **kwargs: Any,
    ) -> ChatResult:
        async def no_cleanup():
            return None

        _, result, _ = await self._race(
            lambda candidate: (
                super(ResilientChatGoogleGenerativeAI, candidate)._agenerate(messages, stop, None, **kwargs),
                no_cleanup,
            )
        )
        return result

    async def _astream(
        self,
        messages: list[BaseMessage],
        stop: list[str] | None = None,
        run_manager: AsyncCallbackManagerForLLMRun | None = None,
        **kwargs: Any,
    ) -> AsyncIterator[ChatGenerationChunk]:
        # The race is on the FIRST chunk: once a model has started answering, its stream is used
        # and the other request is cancelled, so answers are never mixed. Token callbacks are
        # emitted by LangChain core for the chunks yielded here, so the loser never reaches the user.
        _END = object()

        def start_attempt(candidate):
            stream = super(ResilientChatGoogleGenerativeAI, candidate)._astream(messages, stop, None, **kwargs)

            async def first_chunk():
                try:
                    return stream, await stream.__anext__()
                except StopAsyncIteration:
                    return stream, _END

            async def cleanup():
                try:
                    await stream.aclose()
                except Exception:
                    pass

            return first_chunk(), cleanup

        candidate, (stream, first), _ = await self._race(start_attempt)
        if first is _END:
            return
        yield first
        async for chunk in stream:
            yield chunk


def thinking_settings(model_name: str) -> dict:
    """
    Reasoning settings per model family. Gemini 3 models take `thinking_level`; Gemini 2.5 Flash
    models take `thinking_budget` (0 = off). Keeping thinking minimal keeps answers fast.
    """
    level = settings.GEMINI_THINKING_LEVEL or None
    if model_name.startswith("gemini-3"):
        return {"reasoning_effort": level, "thinking_budget": None}
    if model_name.startswith("gemini-2.5-flash") and level == "minimal":
        return {"reasoning_effort": None, "thinking_budget": 0}
    return {"reasoning_effort": None, "thinking_budget": None}


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
