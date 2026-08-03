import secrets

import pytest
from sqlalchemy import func, select

from app.db.session import DatabaseSessionManager
from app.models.user import User


class ExpectedTransactionError(Exception):
    """Test-only failure used to exercise rollback."""


def test_session_scope_rolls_back_failed_transaction(
    database_manager: DatabaseSessionManager,
    reset_database: None,
) -> None:
    del reset_database
    with pytest.raises(ExpectedTransactionError), database_manager.session_scope() as session:
        session.add(
            User(
                email=f"{secrets.token_hex(8)}@example.com",
                full_name=None,
                hashed_password=secrets.token_urlsafe(32),
                is_active=True,
                is_superuser=False,
            )
        )
        session.flush()
        raise ExpectedTransactionError

    with database_manager.session_scope() as session:
        user_count = session.scalar(select(func.count()).select_from(User))

    assert user_count == 0
