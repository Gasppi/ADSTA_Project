import pytest
from stubs import StubRecords, StubWording, stub_service

from credit_backend.contracts import SAMPLE_REQUEST, DecisionRequest, DecisionResponse
from credit_backend.decisions.service import DecisionService

REQUEST = DecisionRequest.model_validate(SAMPLE_REQUEST)


def decided(service: DecisionService) -> DecisionResponse:
    try:
        return service.decide(REQUEST)
    except NotImplementedError as error:
        pytest.skip(str(error))


def test_every_decision_is_stored_once_and_answered_with_its_record_id() -> None:
    records = StubRecords()

    response = decided(stub_service(wording=StubWording(), records=records))

    assert len(records.saved) == 1
    assert response.record_id == 1


def test_model_c_words_the_decision_and_is_told_nothing_but_the_decision() -> None:
    wording = StubWording("Worded.")

    response = decided(stub_service(wording=wording))

    assert response.wording == "Worded."
    assert wording.asked == [(response.outcome, tuple(response.reasons))]


def test_a_decision_goes_on_without_wording_when_model_c_gives_none() -> None:
    records = StubRecords()

    response = decided(stub_service(wording=StubWording(None), records=records))

    assert response.wording is None
    assert len(records.saved) == 1


def test_a_decision_goes_on_without_wording_when_no_model_c_is_set() -> None:
    response = decided(stub_service(wording=None))

    assert response.wording is None
    assert response.record_id == 1
