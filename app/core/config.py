import os
from typing import List, Optional

from pydantic import PostgresDsn, field_validator, ValidationInfo
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # API Configuration
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "Logy-Desk"

    # Environment
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")
    DEBUG: bool = os.getenv("DEBUG", "true").lower() == "true"
    TESTING: bool = os.getenv("TESTING", "false").lower() == "true"

    # Database Configuration
    POSTGRES_SERVER: str = os.getenv("POSTGRES_SERVER", "localhost")
    POSTGRES_USER: str = os.getenv("POSTGRES_USER", "logy")
    POSTGRES_PASSWORD: str = os.getenv("POSTGRES_PASSWORD", "logy-password")
    POSTGRES_DB: str = os.getenv("POSTGRES_DB", "logy_desk_db")
    POSTGRES_PORT: str = os.getenv("POSTGRES_PORT", "5432")
    DATABASE_URI: Optional[PostgresDsn] = None

    # ChromaDB Configuration
    CHROMA_DB_PATH: str = os.getenv("CHROMA_DB_PATH", "./chroma_db")

    # LLM Provider Configuration
    LLM_PROVIDER: str = os.getenv(
        "LLM_PROVIDER", "openrouter"
    )  # 'openai' or 'openrouter'

    # OpenAI Configuration (used as fallback)
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    OPENAI_MODEL: str = os.getenv("OPENAI_MODEL", "openai/gpt-4o-mini")

    # OpenRouter Configuration
    OPENROUTER_API_KEY: str = os.getenv("OPENROUTER_API_KEY", "")
    OPENROUTER_BASE_URL: str = os.getenv(
        "OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1"
    )
    OPENROUTER_MODEL: str = os.getenv("OPENROUTER_MODEL", "google/gemma-3-27b-it:free")

    # CORS
    BACKEND_CORS_ORIGINS: List[str] = ["*"]

    # Token expiration for security
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30  # Default to 30 minutes

    # JWT Security
    SECRET_KEY: str = os.getenv("SECRET_KEY", "super-secret-key") # Change this in production!
    ALGORITHM: str = "HS256"

    @field_validator("DATABASE_URI", mode="before")
    @classmethod
    def assemble_db_connection(cls, v: Optional[str], info: ValidationInfo) -> str:
        if isinstance(v, str):
            return v

        values = info.data
        return (
            f"postgresql+asyncpg://"\
            f"{values.get('POSTGRES_USER')}:"\
            f"{values.get('POSTGRES_PASSWORD')}@"\
            f"{values.get('POSTGRES_SERVER')}:"\
            f"{values.get('POSTGRES_PORT')}/"\
            f"{values.get('POSTGRES_DB')}"
        )

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",  # Ignore extra fields in .env
        case_sensitive=False,
        env_nested_delimiter="__",
        validate_default=True,
        protected_namespaces=(),
    )


# Initialize settings
settings: "Settings" = Settings()  # type: ignore