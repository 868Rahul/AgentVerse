from enum import StrEnum
from typing import TypeAlias

DEFAULT_MODEL = "gemini-3.6-flash"


class OpenAIModelName(StrEnum):
    """https://platform.openai.com/docs/models/gpt-4o"""

    GPT_4O_MINI = "gpt-4o-mini"
    GPT_4O = "gpt-4o"

class DeepseekModelName(StrEnum):
    """https://api-docs.deepseek.com/quick_start/pricing"""
    DEEPSEEK_CHAT = "deepseek-chat"

class OllamaModelName(StrEnum):
    """https://ollama.com/search"""

    OLLAMA_GENERIC = "ollama"

class FakeModelName(StrEnum):
    """Fake model for testing."""
    FAKE = "fake"
    
class TongYiModelName(StrEnum):
    """TongYi model"""
    QWEN_PLUS = "qwen-plus"
    QWEN_MAX = "qwen-max"

class GeminiModelName(StrEnum):
    """https://ai.google.dev/gemini-api/docs/models"""
    GEMINI_3_6_FLASH = "gemini-3.6-flash"
    GEMINI_2_5_FLASH = "gemini-2.5-flash"
    GEMINI_2_5_FLASH_LITE = "gemini-2.5-flash-lite"
    GEMINI_3_5_FLASH_LITE = "gemini-3.5-flash-lite"
    GEMINI_3_1_FLASH_LITE = "gemini-3.1-flash-lite"
    GEMINI_FLASH_LATEST = "gemini-flash-latest"
    



AllModelEnum: TypeAlias = (
    OpenAIModelName
    | DeepseekModelName
    | OllamaModelName
    | FakeModelName
    | TongYiModelName
    | GeminiModelName
)
