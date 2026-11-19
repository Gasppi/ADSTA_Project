"""The calls to the backend, against httpx.MockTransport instead of a running backend."""

import json
from collections.abc import Callable

import httpx
import pytest

from credit_frontend.backend import BackendClient, Failure, FailureKind, Upload

EXTRACTION = {
    "payslip": {"gross": None},
    "debt_register": {"has_loss_certificate": None, "applicant_name": None, "date_of_birth": None},
    "same_applicant": None,
    "checkpoint": "model-b@abc123",
}
DECISION = {
    "outcome": "refused",
    "reasons": ["income_unknown"],
    "wording": None,
    "features": {},
    "default_probability": None,
    "model_version": "baseline",
    "record_id": 12,
}
PAYSLIP = Upload("payslip.pdf", b"%PDF payslip", "application/pdf")
REGISTER = Upload("register.pdf", b"%PDF register", "application/pdf")


def client_for(handler: Callable[[httpx.Request], httpx.Response]) -> BackendClient:
    return BackendClient(
        "http://backend:8000",
        extraction_timeout_seconds=200.0,
        decision_timeout_seconds=90.0,
        transport=httpx.MockTransport(handler),
    )


def test_the_extraction_sends_both_files_with_the_extraction_timeout() -> None:
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200, json=EXTRACTION)

    answer = client_for(handler).extract(PAYSLIP, REGISTER)

    assert answer == EXTRACTION
    (request,) = seen
    assert request.method == "POST"
    assert str(request.url) == "http://backend:8000/extractions"
    body = request.read()
    assert b'name="payslip"; filename="payslip.pdf"' in body
    assert b'name="debt_register"; filename="register.pdf"' in body
    assert b"%PDF payslip" in body and b"%PDF register" in body
    assert request.extensions["timeout"]["read"] == 200.0


def test_a_503_from_the_extraction_comes_back_as_a_failure() -> None:
    detail = "The Information Extraction Service is not available. Try again."

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(503, json={"detail": detail})

    answer = client_for(handler).extract(PAYSLIP, REGISTER)

    assert answer == Failure(FailureKind.STATUS, 503, detail)


def test_the_decision_sends_the_body_as_json_with_the_decision_timeout() -> None:
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200, json=DECISION)

    body = {"entered": {"age": 34, "monthly_income": None}, "extraction_checkpoint": "c"}
    answer = client_for(handler).decide(body)

    assert answer == DECISION
    (request,) = seen
    assert request.method == "POST"
    assert request.url.path == "/decisions"
    assert json.loads(request.read()) == body
    assert request.extensions["timeout"]["read"] == 90.0


def test_one_call_to_decide_is_one_request() -> None:
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(500)

    client_for(handler).decide({"entered": {}})

    assert calls == 1  # no retry, so a failed call never creates a second record


def test_a_422_keeps_the_detail_so_the_page_can_name_the_field() -> None:
    detail = [{"loc": ["body", "entered", "age"], "msg": "Field required", "type": "missing"}]

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(422, json={"detail": detail})

    assert client_for(handler).decide({}) == Failure(FailureKind.STATUS, 422, detail)


def test_a_500_without_json_is_a_failure() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, text="Internal Server Error")

    assert client_for(handler).decide({}) == Failure(FailureKind.STATUS, 500, None)


def test_a_refused_connection_is_no_connection() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("Connection refused", request=request)

    assert client_for(handler).decide({}) == Failure(FailureKind.NO_CONNECTION)
    assert client_for(handler).extract(PAYSLIP, REGISTER) == Failure(FailureKind.NO_CONNECTION)
    assert client_for(handler).recent() == Failure(FailureKind.NO_CONNECTION)


def test_no_connection_in_time_is_no_connection() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectTimeout("timed out", request=request)

    assert client_for(handler).decide({}) == Failure(FailureKind.NO_CONNECTION)


@pytest.mark.parametrize(
    "error",
    [httpx.ReadTimeout, httpx.WriteTimeout, httpx.RemoteProtocolError, httpx.ReadError],
)
def test_a_sent_request_without_an_answer_is_no_answer_in_time(
    error: type[httpx.TransportError],
) -> None:
    # A paused backend accepts the connection and then never answers: a ReadTimeout.
    def handler(request: httpx.Request) -> httpx.Response:
        raise error("no answer", request=request)

    assert client_for(handler).decide({}) == Failure(FailureKind.NO_ANSWER_IN_TIME)
    assert client_for(handler).extract(PAYSLIP, REGISTER) == Failure(FailureKind.NO_ANSWER_IN_TIME)


def test_an_answer_that_is_not_the_contract_is_a_failure() -> None:
    def not_json(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text="<html>")

    def wrong_shape(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"something": "else"})

    assert client_for(not_json).decide({}) == Failure(FailureKind.INVALID_ANSWER, 200)
    assert client_for(wrong_shape).decide({}) == Failure(FailureKind.INVALID_ANSWER, 200)
    assert client_for(wrong_shape).extract(PAYSLIP, REGISTER) == Failure(
        FailureKind.INVALID_ANSWER, 200
    )
    assert client_for(wrong_shape).recent() == Failure(FailureKind.INVALID_ANSWER, 200)


def test_the_recent_list_asks_for_the_last_20() -> None:
    seen: list[httpx.Request] = []
    records = [{"id": 2, "outcome": "approved"}, {"id": 1, "outcome": "refused"}]

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200, json=records)

    answer = client_for(handler).recent()

    assert answer == records
    (request,) = seen
    assert request.method == "GET"
    assert request.url.path == "/decisions/recent"
    assert request.url.params["limit"] == "20"
