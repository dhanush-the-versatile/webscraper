"""Application settings.

All configuration is sourced from environment variables (or a local ``.env``
file) and validated with pydantic-settings. Sensible defaults are provided so
the application boots in development without any external secrets — AI and
data-source integrations degrade gracefully to deterministic fallbacks when
their keys are absent.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import AnyHttpUrl, Field, PostgresDsn, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

Environment = Literal["development", "staging", "production", "test"]
LLMProvider = Literal["auto", "openai", "anthropic", "heuristic"]


class Settings(BaseSettings):
    """Strongly-typed application settings."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    # ---- General ----
    ENVIRONMENT: Environment = "development"
    PROJECT_NAME: str = "Talent Discovery Platform"
    API_V1_PREFIX: str = "/api/v1"
    LOG_LEVEL: str = "INFO"
    LOG_JSON: bool = False

    # ---- Security ----
    SECRET_KEY: str = "dev-secret-key-change-me"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 30
    BACKEND_CORS_ORIGINS: list[AnyHttpUrl] | list[str] = Field(
        default_factory=lambda: ["http://localhost:3000", "http://127.0.0.1:3000"]
    )

    # ---- PostgreSQL ----
    POSTGRES_SERVER: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_USER: str = "talent"
    POSTGRES_PASSWORD: str = "talent"
    POSTGRES_DB: str = "talent"
    DATABASE_URL: str | None = None

    # ---- Redis / Celery ----
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    CELERY_BROKER_URL: str | None = None
    CELERY_RESULT_BACKEND: str | None = None

    # ---- AI ----
    LLM_PROVIDER: LLMProvider = "auto"
    OPENAI_API_KEY: str | None = None
    OPENAI_MODEL: str = "gpt-4o-mini"
    ANTHROPIC_API_KEY: str | None = None
    ANTHROPIC_MODEL: str = "claude-sonnet-5"
    EMBEDDING_MODEL: str = "text-embedding-3-small"
    EMBEDDING_DIM: int = 1536

    # ---- Search / data-source providers ----
    SERPAPI_API_KEY: str | None = None
    BING_SEARCH_API_KEY: str | None = None
    GITHUB_TOKEN: str | None = None

    # ---- Scraping behaviour ----
    SCRAPER_USER_AGENT: str = "TalentDiscoveryBot/1.0 (+https://example.com/bot)"
    SCRAPER_MAX_CONCURRENCY: int = 5
    SCRAPER_REQUEST_TIMEOUT: int = 20
    SCRAPER_MIN_DELAY_SECONDS: float = 1.0
    SCRAPER_MAX_RETRIES: int = 3
    SCRAPER_RESPECT_ROBOTS: bool = True
    SCRAPER_HTTP_PROXY: str | None = None

    # ---- OAuth ----
    GOOGLE_CLIENT_ID: str | None = None
    GOOGLE_CLIENT_SECRET: str | None = None
    GITHUB_CLIENT_ID: str | None = None
    GITHUB_CLIENT_SECRET: str | None = None
    OAUTH_REDIRECT_BASE: str = "http://localhost:3000"

    # ------------------------------------------------------------------ #
    # Validators
    # ------------------------------------------------------------------ #
    @field_validator("BACKEND_CORS_ORIGINS", mode="before")
    @classmethod
    def _split_cors(cls, v: object) -> object:
        """Allow a comma-separated string of origins from the environment."""
        if isinstance(v, str) and not v.startswith("["):
            return [origin.strip() for origin in v.split(",") if origin.strip()]
        return v

    @model_validator(mode="after")
    def _assemble_connections(self) -> Settings:
        """Assemble DB and Celery URLs from parts when not explicitly set."""
        if not self.DATABASE_URL:
            self.DATABASE_URL = str(
                PostgresDsn.build(
                    scheme="postgresql+asyncpg",
                    username=self.POSTGRES_USER,
                    password=self.POSTGRES_PASSWORD,
                    host=self.POSTGRES_SERVER,
                    port=self.POSTGRES_PORT,
                    path=self.POSTGRES_DB,
                )
            )
        if not self.CELERY_BROKER_URL:
            self.CELERY_BROKER_URL = f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/1"
        if not self.CELERY_RESULT_BACKEND:
            self.CELERY_RESULT_BACKEND = f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/2"
        return self

    # ------------------------------------------------------------------ #
    # Convenience properties
    # ------------------------------------------------------------------ #
    @property
    def sync_database_url(self) -> str:
        """Synchronous driver URL (used by Alembic and Celery)."""
        assert self.DATABASE_URL is not None
        return self.DATABASE_URL.replace("+asyncpg", "+psycopg2").replace(
            "postgresql://", "postgresql+psycopg2://"
        )

    @property
    def redis_url(self) -> str:
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"

    @property
    def cors_origins(self) -> list[str]:
        return [str(o).rstrip("/") for o in self.BACKEND_CORS_ORIGINS]

    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT == "production"


@lru_cache
def get_settings() -> Settings:
    """Return a cached Settings singleton."""
    return Settings()


settings = get_settings()
