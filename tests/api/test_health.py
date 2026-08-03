from fastapi.testclient import TestClient


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
