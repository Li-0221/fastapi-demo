import secrets

from fastapi.testclient import TestClient

from tests.support import AccountFixture, login_headers


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

    patch_response = client.patch(
        f"/api/v1/users/{user_id}",
        headers=headers,
        json={"fullName": None, "isActive": False},
    )
    assert patch_response.status_code == 200
    assert patch_response.json()["data"]["fullName"] is None
    assert patch_response.json()["data"]["isActive"] is False

    delete_response = client.delete(f"/api/v1/users/{user_id}", headers=headers)
    assert delete_response.status_code == 204
    assert client.get(f"/api/v1/users/{user_id}", headers=headers).status_code == 404


def test_patch_rejects_null_for_non_nullable_field(
    client: TestClient,
    admin_account: AccountFixture,
    user_account: AccountFixture,
) -> None:
    response = client.patch(
        f"/api/v1/users/{user_account.user.id}",
        headers=login_headers(client, admin_account),
        json={"email": None},
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


def test_self_update_rejects_admin_fields(
    client: TestClient,
    user_account: AccountFixture,
) -> None:
    response = client.patch(
        "/api/v1/users/me",
        headers=login_headers(client, user_account),
        json={"isSuperuser": True},
    )

    assert response.status_code == 422


def test_admin_route_refuses_self_management(
    client: TestClient,
    admin_account: AccountFixture,
) -> None:
    headers = login_headers(client, admin_account)

    patch_response = client.patch(
        f"/api/v1/users/{admin_account.user.id}",
        headers=headers,
        json={"fullName": "Changed"},
    )
    delete_response = client.delete(
        f"/api/v1/users/{admin_account.user.id}",
        headers=headers,
    )

    assert patch_response.status_code == 409
    assert delete_response.status_code == 409


def test_deleted_user_token_stops_working(
    client: TestClient,
    user_account: AccountFixture,
) -> None:
    headers = login_headers(client, user_account)

    assert client.delete("/api/v1/users/me", headers=headers).status_code == 204
    response = client.get("/api/v1/users/me", headers=headers)

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "AUTHENTICATION_REQUIRED"
