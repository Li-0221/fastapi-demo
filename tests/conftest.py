import os
import secrets
from collections.abc import Generator, Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine, create_engine
from testcontainers.community.postgres import PostgresContainer

os.environ.setdefault("APP_SECRET_KEY", secrets.token_urlsafe(48))
os.environ.setdefault("APP_DATABASE_URL", "postgresql+psycopg://localhost/unused")

from app.db.base import Base
from app.db.session import DatabaseSessionManager
from app.dependencies.database import get_database_manager
from app.main import app
from tests.support import AccountFactory, AccountFixture


@pytest.fixture(scope="session")
def postgres_url() -> Iterator[str]:
    with PostgresContainer("postgres:17-alpine", driver="psycopg") as postgres:
        yield postgres.get_connection_url()


@pytest.fixture(scope="session")
def database_engine(postgres_url: str) -> Iterator[Engine]:
    engine = create_engine(postgres_url, pool_pre_ping=True)
    yield engine
    engine.dispose()


@pytest.fixture(scope="session")
def database_manager(database_engine: Engine) -> DatabaseSessionManager:
    return DatabaseSessionManager(database_engine)


@pytest.fixture
def override_application_database(
    database_manager: DatabaseSessionManager,
) -> Generator[None, None, None]:
    def override_database_manager() -> DatabaseSessionManager:
        return database_manager

    app.dependency_overrides[get_database_manager] = override_database_manager
    yield
    app.dependency_overrides.pop(get_database_manager, None)


@pytest.fixture
def reset_database(database_engine: Engine) -> Generator[None, None, None]:
    Base.metadata.create_all(database_engine)
    yield
    Base.metadata.drop_all(database_engine)


@pytest.fixture
def client(
    reset_database: None,
    override_application_database: None,
) -> Generator[TestClient, None, None]:
    del reset_database, override_application_database
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def account_factory(
    database_manager: DatabaseSessionManager,
    reset_database: None,
) -> AccountFactory:
    del reset_database
    return AccountFactory(database_manager)


@pytest.fixture
def user_account(account_factory: AccountFactory) -> AccountFixture:
    return account_factory.create()


@pytest.fixture
def admin_account(account_factory: AccountFactory) -> AccountFixture:
    return account_factory.create(is_superuser=True)
