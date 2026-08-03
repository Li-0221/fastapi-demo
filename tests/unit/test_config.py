import pytest
from pydantic import ValidationError

from app.core.config import AppSettings, DatabaseSettings


def test_secret_key_must_have_minimum_entropy_budget() -> None:
    with pytest.raises(ValidationError):
        AppSettings(secret_key="x" * 31)


def test_database_url_rejects_non_postgresql_driver() -> None:
    with pytest.raises(ValidationError):
        DatabaseSettings(database_url="unsupported")
