import secrets

import pytest
from fastapi.testclient import TestClient

from tests.support import AccountFactory, AccountFixture, login_headers


def test_regular_user_cannot_list_users(
    client: TestClient,
    user_account: AccountFixture,
) -> None:
    response = client.get(
        "/api/v1/users",
        headers=login_headers(client, user_account),
    )

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "PERMISSION_DENIED"


@pytest.mark.parametrize("method", ["post", "get", "put", "delete"])
def test_regular_user_cannot_use_admin_user_routes(
    client: TestClient,
    user_account: AccountFixture,
    admin_account: AccountFixture,
    method: str,
) -> None:
    headers = login_headers(client, user_account)
    user_path = f"/api/v1/users/{admin_account.user.id}"
    if method == "post":
        response = client.post(
            "/api/v1/users",
            headers=headers,
            json={
                "email": "unauthorized@example.com",
                "password": secrets.token_urlsafe(24),
            },
        )
    elif method == "get":
        response = client.get(user_path, headers=headers)
    elif method == "put":
        response = client.put(
            user_path,
            headers=headers,
            json={
                "email": admin_account.user.email,
                "fullName": "Denied",
                "isActive": admin_account.user.is_active,
                "isSuperuser": admin_account.user.is_superuser,
            },
        )
    else:
        response = client.delete(user_path, headers=headers)

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "PERMISSION_DENIED"


def test_admin_user_crud_and_pagination(
    client: TestClient,
    admin_account: AccountFixture,
) -> None:
    headers = login_headers(client, admin_account)
    password = secrets.token_urlsafe(24)
    create_response = client.post(
        "/api/v1/users",
        headers=headers,
        json={
            "email": "managed@example.com",
            "fullName": "Managed User",
            "password": password,
            "isActive": True,
            "isSuperuser": False,
        },
    )
    assert create_response.status_code == 201
    user_id = create_response.json()["data"]["id"]

    list_response = client.get("/api/v1/users?page=1&pageSize=1", headers=headers)
    assert list_response.status_code == 200
    assert list_response.json()["data"]["total"] == 2
    assert list_response.json()["data"]["pageSize"] == 1
    assert len(list_response.json()["data"]["items"]) == 1

    get_response = client.get(f"/api/v1/users/{user_id}", headers=headers)
    assert get_response.status_code == 200
    assert get_response.json()["data"]["fullName"] == "Managed User"

    put_response = client.put(
        f"/api/v1/users/{user_id}",
        headers=headers,
        json={
            "email": "managed@example.com",
            "fullName": None,
            "isActive": False,
            "isSuperuser": False,
        },
    )
    assert put_response.status_code == 200
    assert put_response.json()["data"]["fullName"] is None
    assert put_response.json()["data"]["isActive"] is False

    incomplete_response = client.put(
        f"/api/v1/users/{user_id}",
        headers=headers,
        json={},
    )
    assert incomplete_response.status_code == 422

    delete_response = client.delete(f"/api/v1/users/{user_id}", headers=headers)
    assert delete_response.status_code == 204
    assert client.get(f"/api/v1/users/{user_id}", headers=headers).status_code == 404


def test_put_rejects_null_for_non_nullable_field(
    client: TestClient,
    admin_account: AccountFixture,
    user_account: AccountFixture,
) -> None:
    response = client.put(
        f"/api/v1/users/{user_account.user.id}",
        headers=login_headers(client, admin_account),
        json={
            "email": None,
            "fullName": user_account.user.full_name,
            "isActive": user_account.user.is_active,
            "isSuperuser": user_account.user.is_superuser,
        },
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"
    assert response.json()["error"]["details"][0]["location"] == ["body", "email"]


def test_self_update_rejects_admin_fields(
    client: TestClient,
    user_account: AccountFixture,
) -> None:
    response = client.put(
        "/api/v1/users/me",
        headers=login_headers(client, user_account),
        json={
            "email": user_account.user.email,
            "fullName": user_account.user.full_name,
            "isSuperuser": True,
        },
    )

    assert response.status_code == 422


def test_admin_route_refuses_self_management(
    client: TestClient,
    admin_account: AccountFixture,
) -> None:
    headers = login_headers(client, admin_account)

    put_response = client.put(
        f"/api/v1/users/{admin_account.user.id}",
        headers=headers,
        json={
            "email": admin_account.user.email,
            "fullName": "Changed",
            "isActive": admin_account.user.is_active,
            "isSuperuser": admin_account.user.is_superuser,
        },
    )
    delete_response = client.delete(
        f"/api/v1/users/{admin_account.user.id}",
        headers=headers,
    )

    assert put_response.status_code == 409
    assert delete_response.status_code == 409


def test_current_user_cannot_delete_own_account(
    client: TestClient,
    user_account: AccountFixture,
) -> None:
    headers = login_headers(client, user_account)

    response = client.delete(
        f"/api/v1/users/{user_account.user.id}",
        headers=headers,
    )

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "PERMISSION_DENIED"
    assert client.get("/api/v1/users/me", headers=headers).status_code == 200


def test_current_user_can_replace_profile(
    client: TestClient,
    user_account: AccountFixture,
) -> None:
    response = client.put(
        "/api/v1/users/me",
        headers=login_headers(client, user_account),
        json={
            "email": user_account.user.email,
            "fullName": None,
        },
    )

    assert response.status_code == 200
    assert response.json()["data"]["fullName"] is None


def test_profile_update_cannot_bypass_password_change_contract(
    client: TestClient,
    user_account: AccountFixture,
) -> None:
    response = client.put(
        "/api/v1/users/me",
        headers=login_headers(client, user_account),
        json={
            "email": user_account.user.email,
            "fullName": user_account.user.full_name,
            "password": secrets.token_urlsafe(24),
        },
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


def test_current_user_can_change_password(
    client: TestClient,
    user_account: AccountFixture,
) -> None:
    new_password = secrets.token_urlsafe(24)

    response = client.put(
        "/api/v1/users/me/password",
        headers=login_headers(client, user_account),
        json={
            "currentPassword": user_account.password,
            "newPassword": new_password,
        },
    )

    assert response.status_code == 204
    assert response.content == b""
    old_login = client.post(
        "/api/v1/auth/login/access-token",
        data={"username": user_account.user.email, "password": user_account.password},
    )
    new_login = client.post(
        "/api/v1/auth/login/access-token",
        data={"username": user_account.user.email, "password": new_password},
    )
    assert old_login.status_code == 401
    assert new_login.status_code == 200


def test_password_change_rejects_incorrect_current_password(
    client: TestClient,
    user_account: AccountFixture,
) -> None:
    response = client.put(
        "/api/v1/users/me/password",
        headers=login_headers(client, user_account),
        json={
            "currentPassword": secrets.token_urlsafe(24),
            "newPassword": secrets.token_urlsafe(24),
        },
    )

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "INVALID_CURRENT_PASSWORD"
    original_login = client.post(
        "/api/v1/auth/login/access-token",
        data={"username": user_account.user.email, "password": user_account.password},
    )
    assert original_login.status_code == 200


def test_password_change_requires_authentication(client: TestClient) -> None:
    response = client.put(
        "/api/v1/users/me/password",
        json={
            "currentPassword": secrets.token_urlsafe(24),
            "newPassword": secrets.token_urlsafe(24),
        },
    )

    assert response.status_code == 401
    assert response.headers["WWW-Authenticate"] == "Bearer"
    assert response.json()["error"]["code"] == "AUTHENTICATION_REQUIRED"


def test_disabled_user_token_stops_working(
    client: TestClient,
    user_account: AccountFixture,
    admin_account: AccountFixture,
) -> None:
    user_headers = login_headers(client, user_account)
    response = client.put(
        f"/api/v1/users/{user_account.user.id}",
        headers=login_headers(client, admin_account),
        json={
            "email": user_account.user.email,
            "fullName": user_account.user.full_name,
            "isActive": False,
            "isSuperuser": user_account.user.is_superuser,
        },
    )

    assert response.status_code == 200
    rejected = client.get("/api/v1/users/me", headers=user_headers)
    assert rejected.status_code == 403
    assert rejected.json()["error"]["code"] == "INACTIVE_USER"


def test_user_list_empty_page_is_stable(
    client: TestClient,
    admin_account: AccountFixture,
    account_factory: AccountFactory,
) -> None:
    account_factory.create()
    response = client.get(
        "/api/v1/users?page=2&pageSize=2",
        headers=login_headers(client, admin_account),
    )

    assert response.status_code == 200
    assert response.json()["data"] == {
        "items": [],
        "total": 2,
        "page": 2,
        "pageSize": 2,
    }


def test_user_list_rejects_page_that_exceeds_supported_offset(
    client: TestClient,
    admin_account: AccountFixture,
) -> None:
    response = client.get(
        "/api/v1/users",
        params={"page": 10**100, "pageSize": 100},
        headers=login_headers(client, admin_account),
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"
    assert response.json()["error"]["details"][0]["location"] == ["query", "page"]
