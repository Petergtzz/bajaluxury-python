import os
from datetime import timedelta
from enum import StrEnum
from typing import Self
from urllib.parse import quote

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy import URL


class EmailSenderType(StrEnum):
    logger = "logger"
    resend = "resend"


class Environment(StrEnum):
    development = "development"
    testing = "testing"
    production = "production"


env = Environment(os.getenv("BAJA_ENV", Environment.development))
env_files = (".env", ".env.testing") if env == Environment.testing else (".env",)

DEFAULT_SECRET = "development-secret-do-not-use-in-production"
MIN_SECRET_LENGTH = 32


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="baja_",
        env_file=env_files,
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    ENV: Environment = Environment.development
    SECRET: str = DEFAULT_SECRET

    POSTGRES_USER: str = "baja"
    POSTGRES_PWD: str = ""
    POSTGRES_HOST: str = "127.0.0.1"
    POSTGRES_PORT: int = 5432
    POSTGRES_DATABASE: str = "baja"
    POSTGRES_POOL_SIZE: int = 10
    POSTGRES_MAX_OVERFLOW: int = 20
    SQLALCHEMY_DEBUG: bool = False

    REDIS_HOST: str = "127.0.0.1"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    REDIS_PASSWORD: str = ""

    BASE_URL: str = "http://127.0.0.1:8000"
    FRONTEND_BASE_URL: str = "http://127.0.0.1:3000"

    USER_SESSION_TTL: timedelta = timedelta(days=31)
    USER_SESSION_COOKIE_KEY: str = "baja_session"
    LOGIN_CODE_TTL: timedelta = timedelta(minutes=10)
    LOGIN_CODE_LENGTH: int = 6
    LOGIN_CODE_RATE_LIMIT_WINDOW: timedelta = timedelta(minutes=15)
    LOGIN_CODE_MAX_REQUESTS_PER_WINDOW: int = 5
    LOGIN_CODE_MAX_ATTEMPTS_PER_WINDOW: int = 5
    LOGIN_CODE_MAX_REQUESTS_PER_IP_PER_WINDOW: int = 20

    EMAIL_SENDER: EmailSenderType = EmailSenderType.logger
    EMAIL_FROM: str = "Baja Luxury <noreply@bajaluxurymgmt.com>"
    RESEND_API_KEY: str | None = None
    RESEND_API_URL: str = "https://api.resend.com"

    WORKER_MAX_RETRIES: int = 10
    WORKER_MIN_BACKOFF_MILLISECONDS: int = 2_000
    WORKER_TIME_LIMIT_MILLISECONDS: int = 60_000

    @model_validator(mode="after")
    def validate_production_secret(self) -> Self:
        if self.is_production() and (
            self.SECRET == DEFAULT_SECRET
            or len(self.SECRET.strip()) < MIN_SECRET_LENGTH
        ):
            raise ValueError(
                f"BAJA_SECRET must be set in production, at least {MIN_SECRET_LENGTH} "
                "characters (openssl rand -hex 32)"
            )
        return self

    @model_validator(mode="after")
    def validate_email_sender(self) -> Self:
        if self.EMAIL_SENDER == EmailSenderType.resend and not self.RESEND_API_KEY:
            raise ValueError("BAJA_RESEND_API_KEY must be set to send with Resend")
        if self.is_production() and self.EMAIL_SENDER != EmailSenderType.resend:
            raise ValueError("BAJA_EMAIL_SENDER must be 'resend' in production")
        return self

    def get_redis_url(self) -> str:
        credentials = (
            f":{quote(self.REDIS_PASSWORD, safe='')}@" if self.REDIS_PASSWORD else ""
        )
        return (
            f"redis://{credentials}{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"
        )

    def get_postgres_dsn(self, database: str | None = None) -> str:
        return URL.create(
            drivername="postgresql+asyncpg",
            username=self.POSTGRES_USER,
            password=self.POSTGRES_PWD or None,
            host=self.POSTGRES_HOST,
            port=self.POSTGRES_PORT,
            database=database or self.POSTGRES_DATABASE,
        ).render_as_string(hide_password=False)

    def is_testing(self) -> bool:
        return self.ENV == Environment.testing

    def is_production(self) -> bool:
        return self.ENV == Environment.production


settings = Settings()
