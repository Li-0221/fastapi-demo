from functools import lru_cache
from typing import Annotated, Literal

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

DATABASE_URL_DRIVER_ERROR = "database_url must use postgresql+psycopg"


class AppSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="APP_", extra="ignore")

    name: str = "FastAPI Demo"
    environment: Literal["local", "test", "staging", "production"] = "local"
    api_v1_prefix: str = "/api/v1"
    secret_key: Annotated[SecretStr, Field(min_length=32)]
    access_token_expire_minutes: int = 30


class DatabaseSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="APP_", extra="ignore")

    database_url: SecretStr

    @field_validator("database_url")
    @classmethod
    def require_psycopg_url(cls, value: SecretStr) -> SecretStr:
        if not value.get_secret_value().startswith("postgresql+psycopg://"):
            raise ValueError(DATABASE_URL_DRIVER_ERROR)
        return value

    @property
    def url(self) -> str:
        return self.database_url.get_secret_value()


@lru_cache
def get_app_settings() -> AppSettings:
    return AppSettings()


@lru_cache
def get_database_settings() -> DatabaseSettings:
    return DatabaseSettings()
