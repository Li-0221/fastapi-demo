import anyio
import httpx2
from fastapi.testclient import TestClient

from app.main import app


def test_health_check(client: TestClient) -> None:
    response = client.get("/api/v1/health")

    assert response.status_code == 200
    assert response.json() == {"data": {"status": "ok"}}
    assert response.headers["X-Request-ID"]


def test_openapi_documents_the_runtime_error_contract(client: TestClient) -> None:
    response = client.get("/api/v1/openapi.json")

    assert response.status_code == 200
    schema = response.json()
    validation_schema = schema["paths"]["/api/v1/auth/register"]["post"]["responses"]["422"]
    documented_schema = validation_schema["content"]["application/json"]["schema"]
    assert documented_schema == {"$ref": "#/components/schemas/ErrorResponse"}


def test_openapi_matches_put_and_path_runtime_contract(client: TestClient) -> None:
    schema = client.get("/api/v1/openapi.json").json()
    assert "delete" not in schema["paths"]["/api/v1/users/me"]

    user_path = schema["paths"]["/api/v1/users/{userId}"]
    assert "put" in user_path
    assert "patch" not in user_path
    path_parameters = user_path["get"]["parameters"]
    assert [parameter["name"] for parameter in path_parameters] == ["userId"]

    update_schema = schema["components"]["schemas"]["UserPutRequest"]
    assert set(update_schema["required"]) == {
        "email",
        "fullName",
        "isActive",
        "isSuperuser",
    }
    assert "password" not in update_schema["required"]
    assert {"type": "null"} in update_schema["properties"]["fullName"]["anyOf"]

    self_update_schema = schema["components"]["schemas"]["UserSelfPutRequest"]
    assert set(self_update_schema["required"]) == {"email", "fullName"}


def test_method_not_allowed_keeps_protocol_header(client: TestClient) -> None:
    response = client.post("/api/v1/health")

    assert response.status_code == 405
    assert response.headers["Allow"] == "GET"
    assert response.headers["X-Request-ID"] == response.json()["error"]["requestId"]
    assert response.json()["error"]["code"] == "HTTP_ERROR"


def test_unexpected_error_has_safe_contract_and_request_id() -> None:
    async def raise_unexpected_error() -> None:
        raise RuntimeError

    app.add_api_route("/unexpected", raise_unexpected_error)
    test_route = app.router.routes[-1]

    async def request_unexpected_error() -> httpx2.Response:
        transport = httpx2.ASGITransport(app=app, raise_app_exceptions=False)
        async with httpx2.AsyncClient(
            transport=transport,
            base_url="http://testserver",
        ) as async_client:
            return await async_client.get("/unexpected")

    try:
        response = anyio.run(request_unexpected_error)
    finally:
        app.router.routes.remove(test_route)
        app.openapi_schema = None

    assert response.status_code == 500
    assert response.headers["X-Request-ID"] == response.json()["error"]["requestId"]
    assert response.json()["error"]["code"] == "INTERNAL_ERROR"
    assert response.json()["error"]["message"] == "An unexpected error occurred"
