from fastapi.testclient import TestClient

from backend.app.main import app


def test_health_returns_ok_response_shape():
    client = TestClient(app)

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {
        "data": {
            "status": "ok",
            "service": "945-backend"
        },
        "error": None
    }


def test_cors_preflight_allows_vite_frontend():
    client = TestClient(app)

    response = client.options(
        "/api/today?user_id=demo-user-945&date=2026-07-11",
        headers={
            "Origin": "http://127.0.0.1:8080",
            "Access-Control-Request-Method": "GET"
        }
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://127.0.0.1:8080"
