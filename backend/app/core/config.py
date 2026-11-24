from typing import Annotated, Any, List, Optional
from urllib.parse import quote_plus
from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # App
    PROJECT_NAME: str = "GitLab Support Automation & Triage Platform"
    DEBUG: bool = False
    API_V1_STR: str = "/api/v1"
    SECRET_KEY: str = "dev-secret-key-change-in-production-12345"

    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    CORS_ORIGINS: Annotated[List[str], NoDecode] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ]

    # Auth & RBAC
    JWT_SECRET: str = "dev-jwt-secret-change-in-production-min-32-chars"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 480

    # PostgreSQL with pgvector
    POSTGRES_SERVER: str = "localhost"
    POSTGRES_PORT: int = 5433
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "postgrespassword"
    POSTGRES_DB: str = "app_db"
    DATABASE_URL: Optional[str] = None

    # Redis & Task Queue (ARQ)
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_PASSWORD: Optional[str] = None
    REDIS_URL: str = "redis://localhost:6379/0"

    # GitLab API & Webhooks
    GITLAB_URL: str = "https://gitlab.com"
    GITLAB_PRIVATE_TOKEN: str = "glpat-your-token"
    GITLAB_READ_TOKEN: Optional[str] = None
    GITLAB_WRITE_TOKEN: Optional[str] = None
    GITLAB_WEBHOOK_SECRET: Optional[str] = "your-webhook-secret"
    GITLAB_DEFAULT_PROJECT_ID: Optional[str] = None
    GITLAB_BOT_USERNAME: str = "platform-bot"
    GITLAB_TIMEOUT_SECONDS: float = 15.0
    RECONCILE_INTERVAL_MINUTES: int = 15

    # LLM & Embedding Settings (OpenAI-compatible router)
    LLM_API_KEY: str = "your-llm-api-key"
    LLM_BASE_URL: str = "https://generativelanguage.googleapis.com/v1beta/openai/"
    LLM_MODEL: str = "gemini-2.5-flash"
    LLM_TEMPERATURE: float = 0.2
    LLM_TIMEOUT_SECONDS: float = 45.0
    EMBEDDING_MODEL: str = "text-embedding-3-small"
    EMBEDDING_DIMENSIONS: int = 1536
    EMBEDDING_API_KEY: Optional[str] = None
    EMBEDDING_BASE_URL: Optional[str] = None

    # Triage, RAG & Automation Guardrails
    AUTO_PILOT_CONFIDENCE_THRESHOLD: float = 0.85
    DUPLICATE_SIMILARITY_THRESHOLD: float = 0.82
    RAG_MIN_CONFIDENCE: float = 0.65
    RAG_ABSTENTION_THRESHOLD: float = 0.65
    DRIFT_CLUSTER_SIMILARITY_THRESHOLD: float = 0.80
    ENABLE_AUTO_EXECUTION: bool = False  # Default Co-Pilot mode (approval required)

    # Documentation & Academy Sources + Crawler SSRF Allowlist
    DOCS_BASE_URL: str = "https://docs.example.com"
    ACADEMY_BASE_URL: str = "https://academy.example.com"
    CRAWLER_ALLOWED_DOMAINS: Annotated[List[str], NoDecode] = [
        "docs.example.com",
        "academy.example.com",
        "localhost",
        "127.0.0.1",
    ]

    # Notifications (SLA & Escalation)
    SLACK_WEBHOOK_URL: Optional[str] = None
    MATTERMOST_WEBHOOK_URL: Optional[str] = None

    # SLA Defaults
    SLA_P1_HOURS: int = 1
    SLA_P2_HOURS: int = 4
    SLA_P3_HOURS: int = 24
    SLA_P4_HOURS: int = 72
    SLA_AT_RISK_THRESHOLD_RATIO: float = 0.75

    @field_validator("CORS_ORIGINS", "CRAWLER_ALLOWED_DOMAINS", mode="before")
    @classmethod
    def parse_str_list(cls, v: Any) -> List[str]:
        if isinstance(v, str):
            raw = v.strip()
            if not raw:
                return []
            if raw.startswith("["):
                import json
                parsed = json.loads(raw)
                return [str(item).strip() for item in parsed if str(item).strip() and str(item).strip() != "*"]
            return [item.strip() for item in raw.split(",") if item.strip() and item.strip() != "*"]
        if isinstance(v, list):
            return [str(item).strip() for item in v if str(item).strip() and str(item).strip() != "*"]
        return []

    @model_validator(mode="after")
    def finalize_settings(self) -> "Settings":
        if not self.DATABASE_URL or not self.DATABASE_URL.strip():
            user = quote_plus(self.POSTGRES_USER)
            pwd = quote_plus(self.POSTGRES_PASSWORD)
            self.DATABASE_URL = (
                f"postgresql+asyncpg://{user}:{pwd}@{self.POSTGRES_SERVER}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
            )
        else:
            url = self.DATABASE_URL.strip()
            if url.startswith("postgres://"):
                url = "postgresql+asyncpg://" + url[len("postgres://"):]
            elif url.startswith("postgresql://"):
                url = "postgresql+asyncpg://" + url[len("postgresql://"):]
            self.DATABASE_URL = url

        if not self.GITLAB_READ_TOKEN:
            self.GITLAB_READ_TOKEN = self.GITLAB_PRIVATE_TOKEN
        if not self.GITLAB_WRITE_TOKEN:
            self.GITLAB_WRITE_TOKEN = self.GITLAB_PRIVATE_TOKEN

        if not self.EMBEDDING_API_KEY:
            self.EMBEDDING_API_KEY = self.LLM_API_KEY
        if not self.EMBEDDING_BASE_URL:
            self.EMBEDDING_BASE_URL = self.LLM_BASE_URL

        return self

    @property
    def DATABASE_URL_SYNC(self) -> str:
        url = self.DATABASE_URL or ""
        if "+asyncpg" in url:
            return url.replace("+asyncpg", "+psycopg2", 1)
        if url.startswith("postgres://"):
            return url.replace("postgres://", "postgresql+psycopg2://", 1)
        if url.startswith("postgresql://"):
            return url.replace("postgresql://", "postgresql+psycopg2://", 1)
        return url

    @property
    def effective_gitlab_read_token(self) -> str:
        return self.GITLAB_READ_TOKEN or self.GITLAB_PRIVATE_TOKEN

    @property
    def effective_gitlab_write_token(self) -> str:
        return self.GITLAB_WRITE_TOKEN or self.GITLAB_PRIVATE_TOKEN


settings = Settings()
