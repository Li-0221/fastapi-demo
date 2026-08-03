import secrets
from dataclasses import dataclass, field

from fastapi.testclient import TestClient

from app.db.session import DatabaseSessionManager
from app.services.user import UserService
from app.services.user_contracts import CreateUserCommand, UserResult


@dataclass(frozen=True, slots=True)
class AccountFixture:
    user: UserResult
    password: str = field(repr=False)


class AccountFactory:
    def __init__(self, manager: DatabaseSessionManager) -> None:
        self.manager = manager

    def create(
        self,
        *,
        is_superuser: bool = False,
        is_active: bool = True,
    ) -> AccountFixture:
        password = secrets.token_urlsafe(24)
        email_prefix = secrets.token_hex(8)
        user = UserService(manager=self.manager).create_user(
            CreateUserCommand(
                email=f"{email_prefix}@example.com",
                full_name="Test User",
                password=password,
                is_active=is_active,
                is_superuser=is_superuser,
            )
        )
        return AccountFixture(user=user, password=password)


def login_headers(client: TestClient, account: AccountFixture) -> dict[str, str]:
    response = client.post(
        "/api/v1/auth/login/access-token",
        data={"username": account.user.email, "password": account.password},
    )
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}
