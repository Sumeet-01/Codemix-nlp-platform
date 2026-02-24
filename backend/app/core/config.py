"""
Application Configuration - Pydantic Settings Management
"""
from functools import lru_cache
from typing import List, Optional

from pydantic import field_validator, AnyHttpUrl
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    # ==========================================================================
    # App
    # ==========================================================================
    APP_NAME: str = "CodeMix NLP Platform"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    LOG_LEVEL: str = "INFO"
    VERSION: str = "1.0.0"

    # ==========================================================================
    # Database
    # ==========================================================================
    DATABASE_URL: str = "sqlite+aiosqlite:///./codemix_dev.db"
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "password"
    POSTGRES_DB: str = "codemix_nlp"
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432

    # ==========================================================================
    # Redis (optional — leave empty to disable caching)
    # ==========================================================================
    REDIS_URL: Optional[str] = None
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    CACHE_TTL: int = 3600  # 1 hour

    # ==========================================================================
    # JWT
    # ==========================================================================
    JWT_SECRET_KEY: str = "your-super-secret-key-minimum-32-characters-change-in-production"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    JWT_PRIVATE_KEY_PATH: Optional[str] = None
    JWT_PUBLIC_KEY_PATH: Optional[str] = None

    # ==========================================================================
    # URLs
    # ==========================================================================
    FRONTEND_URL: str = "http://localhost:3000"
    BACKEND_URL: str = "http://localhost:8000"

    # ==========================================================================
    # ML Model
    # ==========================================================================
    MODEL_PATH: str = "./ml/models/checkpoints/best_model"
    MODEL_NAME: str = "xlm-roberta-large"
    MAX_LENGTH: int = 128
    BATCH_SIZE: int = 16
    INFERENCE_TIMEOUT: int = 30  # seconds
    DEMO_MODE: bool = True  # True = skip torch/transformers, return mock predictions

    # ==========================================================================
    # Celery (optional)
    # ==========================================================================
    CELERY_BROKER_URL: Optional[str] = None
    CELERY_RESULT_BACKEND: Optional[str] = None

    # ==========================================================================
    # Rate Limiting
    # ==========================================================================
    RATE_LIMIT_REQUESTS: int = 10
    RATE_LIMIT_WINDOW: int = 60  # seconds

    # ==========================================================================
    # OAuth (Optional)
    # ==========================================================================
    GOOGLE_CLIENT_ID: Optional[str] = None
    GOOGLE_CLIENT_SECRET: Optional[str] = None
    GITHUB_CLIENT_ID: Optional[str] = None
    GITHUB_CLIENT_SECRET: Optional[str] = None

    # ==========================================================================
    # Computed Properties
    # ==========================================================================
    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT == "production"

    @property
    def allowed_origins(self) -> List[str]:
        if self.DEBUG:
            return ["*"]
        return [self.FRONTEND_URL]


@lru_cache()
def get_settings() -> Settings:
    """Get cached application settings."""
    return Settings()


settings = get_settings()
