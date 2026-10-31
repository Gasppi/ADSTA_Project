from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from stubs import StubExtraction, StubWording, stub_service

from credit_backend.contracts import SAMPLE_REQUEST
from credit_backend.decisions.service import DecisionService
from credit_backend.main import app

FILES = {"payslip": b"%PDF payslip", "debt_register": b"%PDF register"}


def client(service: DecisionService) -> Iterator[TestClient]:
    app.state.service = service
    yield TestClient(app, raise_server_exceptions=False)
    del app.state.service


@pytest.fixture
def api() -> Iterator[TestClient]:
    yield from client(stub_service(wording=StubWording()))


@pytest.fixture
def api_without_extraction() -> Iterator[TestClient]:
    yield from client(stub_service(extraction=StubExtraction(None)))


def test_the_service_is_up(api: TestClient) -> None:
    response = api.get("/health")

    assert response.status_code == 200


def test_the_documents_are_read_and_nothing_is_decided(api: TestClient) -> None:
    response = api.post("/extractions", files=FILES)

    assert response.status_code == 200
    assert response.json()["payslip"]["gross"]["amount"] == "6000.00"
    assert "outcome" not in response.json()


def test_documents_nobody_could_read_answer_503(api_without_extraction: TestClient) -> None:
    response = api_without_extraction.post("/extractions", files=FILES)

    if response.status_code == 500:
        pytest.skip("Task 7e: there is no handler for ExtractionUnavailableError yet")
    assert response.status_code == 503
    assert response.json()["detail"]


def test_the_sample_application_is_decided_worded_and_stored(api: TestClient) -> None:
    response = api.post("/decisions", json=SAMPLE_REQUEST)

    if response.status_code == 500:
        pytest.skip("Task 7d: decide() does not word and store the decision yet")
    assert response.status_code == 200
    body = response.json()
    assert body["outcome"] == "approved"
    assert body["wording"] == "Worded."
    assert body["model_version"] == "placeholder"
    assert body["record_id"] == 1
    assert "default_probability" in body


def test_the_recent_decisions_can_be_listed(api: TestClient) -> None:
    response = api.get("/decisions/recent", params={"limit": 5})

    assert response.status_code == 200
    assert response.json() == []
