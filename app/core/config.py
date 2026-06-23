from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = "Arshin Excel Checker"
    app_env: str = Field(default="dev", alias="APP_ENV")
    app_host: str = Field(default="0.0.0.0", alias="APP_HOST")
    app_port: int = Field(default=8000, alias="APP_PORT")
    app_debug: bool = Field(default=True, alias="APP_DEBUG")
    api_prefix: str = Field(default="/api", alias="API_PREFIX")

    secret_key: str = Field(default="change-me", alias="SECRET_KEY")
    access_token_expire_minutes: int = Field(default=60, alias="ACCESS_TOKEN_EXPIRE_MINUTES")
    algorithm: str = Field(default="HS256", alias="JWT_ALGORITHM")

    postgres_host: str = Field(default="postgres", alias="POSTGRES_HOST")
    postgres_port: int = Field(default=5432, alias="POSTGRES_PORT")
    postgres_db: str = Field(default="arshin", alias="POSTGRES_DB")
    postgres_user: str = Field(default="arshin", alias="POSTGRES_USER")
    postgres_password: str = Field(default="arshin", alias="POSTGRES_PASSWORD")

    redis_host: str = Field(default="redis", alias="REDIS_HOST")
    redis_port: int = Field(default=6379, alias="REDIS_PORT")
    redis_db: int = Field(default=0, alias="REDIS_DB")

    minio_endpoint: str = Field(default="minio:9000", alias="MINIO_ENDPOINT")
    minio_access_key: str = Field(default="minioadmin", alias="MINIO_ACCESS_KEY")
    minio_secret_key: str = Field(default="minioadmin", alias="MINIO_SECRET_KEY")
    minio_bucket_source: str = Field(default="source-files", alias="MINIO_BUCKET_SOURCE")
    minio_bucket_result: str = Field(default="result-files", alias="MINIO_BUCKET_RESULT")
    minio_secure: bool = Field(default=False, alias="MINIO_SECURE")

    celery_broker_url: str | None = Field(default=None, alias="CELERY_BROKER_URL")
    celery_result_backend: str | None = Field(default=None, alias="CELERY_RESULT_BACKEND")

    arshin_base_url: str = Field(
        default="https://fgis.gost.ru/fundmetrology/eapi/vri",
        alias="ARSHIN_BASE_URL",
    )
    arshin_timeout_connect: float = Field(default=5.0, alias="ARSHIN_TIMEOUT_CONNECT")
    arshin_timeout_read: float = Field(default=20.0, alias="ARSHIN_TIMEOUT_READ")
    arshin_timeout_seconds: float = Field(default=20.0, alias="ARSHIN_TIMEOUT_SECONDS")
    arshin_backoff_seconds: float = Field(default=2.0, alias="ARSHIN_BACKOFF_SECONDS")
    arshin_max_retries: int = Field(default=4, alias="ARSHIN_MAX_RETRIES")

    default_template_code: str = Field(default="pril_1_main", alias="DEFAULT_TEMPLATE_CODE")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")


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


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
