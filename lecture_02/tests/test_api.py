from fastapi.testclient import TestClient

from credit_backend.contracts import SAMPLE_REQUEST
from credit_backend.main import app


def test_the_service_is_up() -> None:
    with TestClient(app) as client:
        response = client.get("/health")

    assert response.status_code == 200


def test_the_sample_application_is_approved() -> None:
    with TestClient(app) as client:
        response = client.post("/decisions", json=SAMPLE_REQUEST)

    assert response.status_code == 200
    assert response.json()["outcome"] == "approved"
    assert response.json()["features"]["age"] == 34.0
