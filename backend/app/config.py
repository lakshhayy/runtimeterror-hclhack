"""App settings, read from backend/.env."""
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

ENV_FILE = Path(__file__).resolve().parent.parent / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=ENV_FILE, env_file_encoding="utf-8", extra="ignore")

    DATABASE_URL: str
    JWT_SECRET: str = "change-me-to-a-long-random-string"
    JWT_EXPIRE_MINUTES: int = 480

    LLM_PROVIDER: str = "openai"  # "openai", "gemini" or "groq"
    OPENAI_API_KEY: str = ""
    GEMINI_API_KEY: str = ""
    GROQ_API_KEY: str = ""
    LLM_MODEL: str = "gpt-4o-mini"
    EMBED_PROVIDER: str = ""  # "openai", "gemini" or "local"; empty = same as LLM_PROVIDER (groq -> local)
    EMBED_MODEL: str = "text-embedding-3-small"
    EMBED_DIM: int = 768

    RAG_MIN_SCORE: float = 0.35
    RAG_HIGH_SCORE: float = 0.55

    CORS_ORIGINS: str = "http://localhost:5173,http://127.0.0.1:5173"
    POLICY_DIR: str = "policies"
    UPLOAD_DIR: str = "uploads"

    # Document storage: "local" (UPLOAD_DIR) or "supabase" (private bucket; needed when deployed)
    STORAGE_BACKEND: str = "local"
    SUPABASE_URL: str = ""
    SUPABASE_SERVICE_KEY: str = ""
    STORAGE_BUCKET: str = "loan-documents"

    @property
    def cors_origins_list(self) -> list[str]:
        """CORS_ORIGINS is comma-separated in .env."""
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]


settings = Settings()
