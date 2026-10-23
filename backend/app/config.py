"""App settings, read from backend/.env."""
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

ENV_FILE = Path(__file__).resolve().parent.parent / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=ENV_FILE, env_file_encoding="utf-8", extra="ignore")

    DATABASE_URL: str
    JWT_SECRET: str = "change-me-to-a-long-random-string"
    JWT_EXPIRE_MINUTES: int = 480

    LLM_PROVIDER: str = "openai"  # "openai" or "gemini"
    OPENAI_API_KEY: str = ""
    GEMINI_API_KEY: str = ""
    LLM_MODEL: str = "gpt-4o-mini"
    EMBED_MODEL: str = "text-embedding-3-small"
    EMBED_DIM: int = 768

    RAG_MIN_SCORE: float = 0.35
    RAG_HIGH_SCORE: float = 0.55

    CORS_ORIGINS: str = "http://localhost:5173"
    POLICY_DIR: str = "policies"
    UPLOAD_DIR: str = "uploads"

    @property
    def cors_origins_list(self) -> list[str]:
        """CORS_ORIGINS is comma-separated in .env."""
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]


settings = Settings()
