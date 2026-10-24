"""
config settings
"""

from pathlib import Path

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from dotenv import find_dotenv

# backend/ directory, relative paths in .env are resolved against it
BACKEND_DIR = Path(__file__).resolve().parents[2]



class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=find_dotenv(),
        env_file_encoding="utf-8",
        env_ignore_empty=True,
        extra="ignore",
        validate_default=False,
    )

    APP_NAME: str = "AgentVerse"
    DEBUG: bool = True
    DATABASE_URL: str | None = None
    HOST: str = "127.0.0.1"
    PORT: int = 8000
    DEV: bool = True

    DEEPSEEK_API_KEY: str | None = None
    OLLAMA_BASE_URL: str | None = None
    OLLAMA_MODEL: str | None = None

    GOOGLE_API_KEY: str | None = None

    DEFAULT_MODEL: str = "gemini-3.6-flash"

    # Gemini free tier resilience
    # Comma separated models tried in order when the primary model is rate limited,
    # overloaded or unavailable. Free tier quotas are counted per model.
    # (gemini-flash-latest is not listed: it took 50-80 s per call on the free tier)
    GEMINI_FALLBACK_MODELS: str = "gemini-3.5-flash-lite,gemini-3.1-flash-lite,gemini-2.5-flash"
    # Attempts per model (1 = no retry). Switching to the next model is faster than waiting
    # for the same overloaded / rate limited model again.
    GEMINI_MAX_RETRIES: int = 1
    GEMINI_TIMEOUT_SECONDS: float = 60
    # Client side throttle shared by all Gemini calls, keeps us under the free tier RPM. 0 disables it
    GEMINI_REQUESTS_PER_MINUTE: float = 30
    # Calls allowed back to back before the throttle starts spacing them
    GEMINI_BURST_REQUESTS: int = 5
    # If a model has not started answering after this many seconds, also send the request to the
    # next model and use whichever answers first (free tier queues are often 10-30 s). 0 disables it
    GEMINI_HEDGE_AFTER_SECONDS: float = 6
    # Reasoning depth: "minimal" keeps answers fast (Gemini 3: thinking_level, Gemini 2.5 Flash:
    # thinking off). Empty = the model's own default
    GEMINI_THINKING_LEVEL: str = "minimal"

    # Print every LangChain step to the console (very noisy, slows streaming down)
    LANGCHAIN_DEBUG: bool = False

    # Guardrails
    MAX_INPUT_CHARS: int = 4000
    # Only the most recent messages of a thread are sent to the model
    MAX_HISTORY_MESSAGES: int = 20
    # Max LangGraph steps per request, stops endless tool loops from burning the quota
    AGENT_RECURSION_LIMIT: int = 12

    # Handbook RAG
    # "google" (Gemini embeddings, no local service needed) or "ollama" (local EMBEDDING_MODEL, e.g. bge-m3)
    EMBEDDING_PROVIDER: str = "google"
    GOOGLE_EMBEDDING_MODEL: str = "gemini-embedding-001"
    EMBEDDING_MODEL: str | None = None
    HANDBOOK_PDF_PATH: str = "resource/EmployeeHandbook.pdf"

    CHROMA_PATH: str = "resource/chroma_db"

    @model_validator(mode="after")
    def _resolve_relative_paths(self):
        """Make the sqlite file and ChromaDB folder independent of the directory the server is started from."""
        sqlite_prefix = "sqlite+aiosqlite:///"
        if self.DATABASE_URL and self.DATABASE_URL.startswith(sqlite_prefix):
            db_path = Path(self.DATABASE_URL.removeprefix(sqlite_prefix))
            if not db_path.is_absolute():
                self.DATABASE_URL = sqlite_prefix + (BACKEND_DIR / db_path).as_posix()
        if self.CHROMA_PATH and not Path(self.CHROMA_PATH).is_absolute():
            self.CHROMA_PATH = (BACKEND_DIR / self.CHROMA_PATH).as_posix()
        if not Path(self.HANDBOOK_PDF_PATH).is_absolute():
            self.HANDBOOK_PDF_PATH = (BACKEND_DIR / self.HANDBOOK_PDF_PATH).as_posix()
        return self

    def is_dev(self):
        return self.DEV

    def gemini_fallback_models(self) -> list[str]:
        return [m.strip() for m in self.GEMINI_FALLBACK_MODELS.split(",") if m.strip()]



settings = Settings()
