from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # --- App ---
    app_name: str = Field(default="Arshin Excel Checker", alias="APP_NAME")
    app_env: str = Field(default="dev", alias="APP_ENV")
    app_host: str = Field(default="0.0.0.0", alias="APP_HOST")
    app_port: int = Field(default=8000, alias="APP_PORT")
    app_debug: bool = Field(default=False, alias="APP_DEBUG")
    api_prefix: str = Field(default="/api", alias="API_PREFIX")

    secret_key: str = Field(default="change-me", alias="APP_SECRET_KEY")
    access_token_expire_minutes: int = Field(default=60 * 24, alias="ACCESS_TOKEN_EXPIRE_MINUTES")
    algorithm: str = Field(default="HS256", alias="JWT_ALGORITHM")

    # --- Postgres ---
    postgres_host: str = Field(default="postgres", alias="POSTGRES_HOST")
    postgres_port: int = Field(default=5432, alias="POSTGRES_PORT")
    postgres_db: str = Field(default="arshin", alias="POSTGRES_DB")
    postgres_user: str = Field(default="arshin", alias="POSTGRES_USER")
    postgres_password: str = Field(default="arshin", alias="POSTGRES_PASSWORD")

    # --- Redis ---
    redis_host: str = Field(default="redis", alias="REDIS_HOST")
    redis_port: int = Field(default=6379, alias="REDIS_PORT")
    redis_db: int = Field(default=0, alias="REDIS_DB")

    # --- Storage (локальный диск, НЕ MinIO — ТЗ §2.3, §5) ---
    storage_root: Path = Field(default=Path("/app/storage"), alias="STORAGE_ROOT")
    max_upload_mb: int = Field(default=25, alias="MAX_UPLOAD_MB")

    # --- Arshin API (ТЗ §1, §9, §17) ---
    arshin_api_mode: str = Field(default="xcdb", alias="ARSHIN_API_MODE")
    arshin_xcdb_url: str = Field(
        default="https://fgis.gost.ru/fundmetrology/cm/xcdb/vri/select",
        alias="ARSHIN_XCDB_URL",
    )
    arshin_eapi_url: str = Field(
        default="https://fgis.gost.ru/fundmetrology/eapi/vri",
        alias="ARSHIN_EAPI_URL",
    )
    arshin_card_url: str = Field(
        default="https://fgis.gost.ru/fundmetrology/cm/results",
        alias="ARSHIN_CARD_URL",
    )
    arshin_rows: int = Field(default=100, alias="ARSHIN_ROWS")
    arshin_request_delay_ms: int = Field(default=1000, alias="ARSHIN_REQUEST_DELAY_MS")
    arshin_timeout_connect: float = Field(default=5.0, alias="ARSHIN_TIMEOUT_CONNECT")
    arshin_timeout_read: float = Field(default=20.0, alias="ARSHIN_TIMEOUT_READ")
    arshin_max_retries: int = Field(default=4, alias="ARSHIN_MAX_RETRIES")
    arshin_backoff_seconds: float = Field(default=2.0, alias="ARSHIN_BACKOFF_SECONDS")
    arshin_year_sweep: bool = Field(default=False, alias="ARSHIN_YEAR_SWEEP")

    # --- Celery ---
    celery_broker_url: str | None = Field(default=None, alias="CELERY_BROKER_URL")
    celery_result_backend: str | None = Field(default=None, alias="CELERY_RESULT_BACKEND")

    # --- Templates / Seed ---
    default_template_code: str = Field(default="pril_1_main", alias="DEFAULT_TEMPLATE_CODE")
    seed_admin_email: str = Field(default="", alias="SEED_ADMIN_EMAIL")
    seed_admin_password: str = Field(default="", alias="SEED_ADMIN_PASSWORD")

    # --- Logging ---
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")

    # --- Derived URLs ---
    @property
    def database_url(self) -> str:
        return (
            f"postgresql+psycopg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @property
    def sync_database_url(self) -> str:
        return self.database_url

    @property
    def redis_url(self) -> str:
        return f"redis://{self.redis_host}:{self.redis_port}/{self.redis_db}"

    @property
    def broker_url(self) -> str:
        return self.celery_broker_url or self.redis_url

    @property
    def result_backend(self) -> str:
        return self.celery_result_backend or self.redis_url

    @property
    def uploads_dir(self) -> Path:
        return self.storage_root / "uploads"

    @property
    def results_dir(self) -> Path:
        return self.storage_root / "results"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
