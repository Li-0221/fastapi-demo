from alembic.config import Config
from sqlalchemy import Engine, inspect

from alembic import command
from app.core.config import get_database_settings
from app.db.base import Base


def test_migration_upgrade_and_downgrade(
    postgres_url: str,
    database_engine: Engine,
    monkeypatch,
) -> None:
    Base.metadata.drop_all(database_engine)
    monkeypatch.setenv("APP_DATABASE_URL", postgres_url)
    get_database_settings.cache_clear()
    config = Config("alembic.ini")

    command.upgrade(config, "head")
    assert inspect(database_engine).has_table("users")

    command.downgrade(config, "base")
    assert not inspect(database_engine).has_table("users")
    get_database_settings.cache_clear()
