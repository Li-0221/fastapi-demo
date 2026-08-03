import anyio
import pytest

from app.db.session import DatabaseSessionManager
from app.dependencies.database import get_database_manager
from app.main import create_app


class ExpectedDisposalError(Exception):
    """Test-only failure used to verify lifespan cleanup."""


def test_application_disposes_cached_database_manager_on_shutdown(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    disposed_managers: list[DatabaseSessionManager] = []
    dispose_manager = DatabaseSessionManager.dispose

    def record_disposal(manager: DatabaseSessionManager) -> None:
        disposed_managers.append(manager)
        dispose_manager(manager)

    get_database_manager.cache_clear()
    monkeypatch.setattr(DatabaseSessionManager, "dispose", record_disposal, raising=False)

    async def run_application_lifespan() -> DatabaseSessionManager:
        application = create_app()
        async with application.router.lifespan_context(application):
            manager = get_database_manager()
            assert disposed_managers == []
            return manager

    manager = anyio.run(run_application_lifespan)
    assert disposed_managers == [manager]
    assert get_database_manager.cache_info().currsize == 0


def test_application_clears_cached_manager_when_disposal_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail_disposal(manager: DatabaseSessionManager) -> None:
        del manager
        raise ExpectedDisposalError

    get_database_manager.cache_clear()
    monkeypatch.setattr(DatabaseSessionManager, "dispose", fail_disposal)

    async def run_application_lifespan() -> None:
        application = create_app()
        async with application.router.lifespan_context(application):
            get_database_manager()

    with pytest.raises(ExpectedDisposalError):
        anyio.run(run_application_lifespan)

    assert get_database_manager.cache_info().currsize == 0
