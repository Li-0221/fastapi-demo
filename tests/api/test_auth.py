import secrets

from fastapi.testclient import TestClient

from tests.support import AccountFactory


def test_register_login_and_read_current_user(client: TestClient) -> None:
    password = secrets.token_urlsafe(24)
    register_response = client.post(
        "/api/v1/auth/register",
        json={
            "email": "LEARNER@example.com",
            "fullName": "FastAPI Learner",
            "password": password,
        },
    )

    assert register_response.status_code == 201
    user_data = register_response.json()["data"]
    assert set(user_data) == {
        "id",
        "email",
        "fullName",
        "isActive",
        "isSuperuser",
        "createdAt",
        "updatedAt",
    }
    assert user_data["email"] == "learner@example.com"
    assert user_data["isSuperuser"] is False
    assert "password" not in user_data

    login_response = client.post(
        "/api/v1/auth/login/access-token",
        data={"username": "learner@example.com", "password": password},
    )

    assert login_response.status_code == 200
    assert set(login_response.json()) == {"access_token", "token_type", "expires_in"}
    token = login_response.json()["access_token"]
    me_response = client.get(
        "/api/v1/users/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert me_response.status_code == 200
    assert me_response.json()["data"]["id"] == user_data["id"]


def test_duplicate_registration_has_stable_conflict_error(client: TestClient) -> None:
    password = secrets.token_urlsafe(24)
    payload = {"email": "duplicate@example.com", "password": password}

    assert client.post("/api/v1/auth/register", json=payload).status_code == 201
    response = client.post("/api/v1/auth/register", json=payload)

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "EMAIL_ALREADY_EXISTS"
    assert response.json()["error"]["requestId"]


def test_invalid_credentials_return_401_and_bearer_challenge(
    client: TestClient,
    account_factory: AccountFactory,
) -> None:
    account = account_factory.create()

    response = client.post(
        "/api/v1/auth/login/access-token",
        data={"username": account.user.email, "password": secrets.token_urlsafe(24)},
    )

    assert response.status_code == 401
    assert response.headers["WWW-Authenticate"] == "Bearer"
    assert response.json()["error"]["code"] == "INVALID_CREDENTIALS"


def test_login_rejects_oversized_credentials(client: TestClient) -> None:
    response = client.post(
        "/api/v1/auth/login/access-token",
        data={"username": "x" * 256, "password": "x" * 129},
    )

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "INVALID_CREDENTIALS"


def test_inactive_user_cannot_log_in(
    client: TestClient,
    account_factory: AccountFactory,
) -> None:
    account = account_factory.create(is_active=False)

    response = client.post(
        "/api/v1/auth/login/access-token",
        data={"username": account.user.email, "password": account.password},
    )

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "INACTIVE_USER"


def test_missing_token_uses_unified_error_contract(client: TestClient) -> None:
    response = client.get("/api/v1/users/me")

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "AUTHENTICATION_REQUIRED"
    assert response.headers["X-Request-ID"] == response.json()["error"]["requestId"]


def test_malformed_token_uses_bearer_challenge(client: TestClient) -> None:
    response = client.get(
        "/api/v1/users/me",
        headers={"Authorization": "Bearer not-a-jwt"},
    )

    assert response.status_code == 401
    assert response.headers["WWW-Authenticate"] == "Bearer"
    assert response.json()["error"]["code"] == "AUTHENTICATION_REQUIRED"


def test_request_body_rejects_python_field_names(client: TestClient) -> None:
    response = client.post(
        "/api/v1/auth/register",
        json={
            "email": "snake-case@example.com",
            "full_name": "Not part of the wire contract",
            "password": secrets.token_urlsafe(24),
        },
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"
