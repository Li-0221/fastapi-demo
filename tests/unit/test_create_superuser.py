import secrets
from collections.abc import Iterator
from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.scripts import create_superuser

type CreateUserCall = tuple[str, str | None, str, bool, bool]


def test_main_creates_active_superuser(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    password = secrets.token_urlsafe(24)
    user_id = uuid4()
    expected_manager = object()
    answers: Iterator[str] = iter(["  admin@example.com  ", "  Admin User  "])
    captured_call: CreateUserCall | None = None

    class UserServiceStub:
        def __init__(self, *, manager: object) -> None:
            assert manager is expected_manager

        def create_user(
            self,
            *,
            email: str,
            full_name: str | None,
            password: str,
            is_active: bool,
            is_superuser: bool,
        ) -> SimpleNamespace:
            nonlocal captured_call
            captured_call = (email, full_name, password, is_active, is_superuser)
            return SimpleNamespace(id=user_id)

    monkeypatch.setattr("builtins.input", lambda prompt: next(answers))
    monkeypatch.setattr(create_superuser, "getpass", lambda prompt: password)
    monkeypatch.setattr(create_superuser, "get_database_manager", lambda: expected_manager)
    monkeypatch.setattr(create_superuser, "UserService", UserServiceStub)

    create_superuser.main()

    assert captured_call == (
        "admin@example.com",
        "Admin User",
        password,
        True,
        True,
    )
    assert capsys.readouterr().out == f"Created superuser: {user_id}\n"
