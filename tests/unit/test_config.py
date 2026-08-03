import pytest
from pydantic import ValidationError

from app.core.config import AppSettings, DatabaseSettings, get_database_settings
from app.main import create_app


def test_secret_key_must_have_minimum_length() -> None:
    with pytest.raises(ValidationError):
        AppSettings(secret_key="x" * 31)


@pytest.mark.parametrize("minutes", [-1, 0, 1441])
def test_access_token_expiry_must_stay_within_policy(minutes: int) -> None:
    with pytest.raises(ValidationError):
        AppSettings(secret_key="x" * 32, access_token_expire_minutes=minutes)


def test_database_url_rejects_non_postgresql_driver() -> None:
    with pytest.raises(ValidationError):
        DatabaseSettings(database_url="unsupported")


def test_application_requires_database_configuration(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("APP_DATABASE_URL", raising=False)
    get_database_settings.cache_clear()
    try:
        with pytest.raises(ValidationError):
            create_app()
    finally:
        get_database_settings.cache_clear()
