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
