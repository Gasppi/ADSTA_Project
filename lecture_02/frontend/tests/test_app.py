"""The page itself, run by Streamlit's AppTest with a fake backend.

AppTest cannot upload files, so the tests that need read documents put the answer of
POST /extractions into st.session_state, where the page keeps it after an upload.
"""

from pathlib import Path
from typing import Any

import pytest
from streamlit.testing.v1 import AppTest
from streamlit.testing.v1.errors import AppTestError

from credit_frontend import logic
from credit_frontend.backend import BackendClient, Failure, FailureKind
from credit_frontend.logic import LossCertificate

APP = Path(__file__).parents[1] / "src" / "credit_frontend" / "app.py"

EXTRACTION = {
    "payslip": {"gross": {"amount": "6000.00", "currency": "CHF", "period": "monthly"}},
    "debt_register": {
        "has_loss_certificate": False,
        "applicant_name": "Anna Muster",
        "date_of_birth": "1990-04-01",
    },
    "same_applicant": True,
    "checkpoint": "model-b@abc123",
}
DECISION = {
    "outcome": "refused",
    "reasons": ["loss_certificate_unknown"],
    "wording": "We cannot grant the credit at this time.",
    "features": {},
    "default_probability": None,
    "model_version": "baseline",
    "record_id": 41,
}
RECORD = {
    "id": 41,
    "created_at": "2026-11-19T14:03:05Z",
    "outcome": "refused",
    "reasons": ["loss_certificate_unknown"],
}


class FakeBackend:
    def __init__(self) -> None:
        self.decisions: list[dict[str, Any]] = []
        self.recent_calls = 0
        self.decision_answer: Any = DECISION
        self.recent_answer: Any = []

    def decide(self, body: dict[str, Any]) -> Any:
        self.decisions.append(body)
        if not isinstance(self.decision_answer, Failure):
            self.recent_answer = [RECORD]
        return self.decision_answer

    def recent(self, limit: int = 20) -> Any:
        self.recent_calls += 1
        return self.recent_answer

    def extract(self, *args: Any) -> Any:
        raise AssertionError("AppTest cannot upload, so the page must not read documents here")


@pytest.fixture
def backend(monkeypatch: pytest.MonkeyPatch) -> FakeBackend:
    monkeypatch.setenv("BACKEND_URL", "http://backend:8000")
    monkeypatch.setenv("EXTRACTION_TIMEOUT_SECONDS", "200")
    monkeypatch.setenv("DECISION_TIMEOUT_SECONDS", "90")
    fake = FakeBackend()
    monkeypatch.setattr(BackendClient, "decide", fake.decide)
    monkeypatch.setattr(BackendClient, "recent", fake.recent)
    monkeypatch.setattr(BackendClient, "extract", fake.extract)
    return fake


def page(extraction: dict[str, Any] | None = None) -> AppTest:
    app = AppTest.from_file(str(APP), default_timeout=30)
    if extraction is not None:
        app.session_state["extraction"] = extraction
        gross = extraction["payslip"]["gross"]
        app.session_state["income_amount"] = logic.read_income_amount(gross)
        app.session_state["income_period"] = gross["period"] if gross else None
        app.session_state["loss_certificate"] = logic.loss_certificate_choice(
            extraction["debt_register"]["has_loss_certificate"]
        )
    return app.run()


def decide_button(app: AppTest) -> Any:
    (button,) = [button for button in app.button if button.label == "Decide"]
    return button


def fill_the_rest(app: AppTest) -> AppTest:
    for name, value in {
        "age": 34,
        "dependants": 1,
        "open_credit_lines": 3,
        "real_estate_lines": 0,
        "late_30_59": 0,
        "late_60_89": 0,
        "late_90": 0,
        "revolving_utilisation": 0.30,
        "monthly_debt_obligations": 1200.0,
    }.items():
        app.number_input(key=name).set_value(value)
    return app.run()


def all_text(app: AppTest) -> str:
    parts = [element.value for element in app.markdown]
    parts += [element.value for element in app.caption]
    parts += [element.value for element in app.text]
    for kind in (app.error, app.warning, app.info, app.success):
        parts += [element.value for element in kind]
    return "\n".join(str(part) for part in parts)


def test_at_the_start_every_number_field_is_empty_and_decide_is_disabled(
    backend: FakeBackend,
) -> None:
    app = page()

    assert not app.exception
    assert all(field.value is None for field in app.number_input)
    assert len(app.number_input) == 10
    assert app.radio(key="loss_certificate").value is None
    assert decide_button(app).disabled
    assert app.info[0].value == "No decisions yet."
    assert backend.recent_calls == 1


def test_the_recent_list_loads_once_and_not_on_every_rerun(backend: FakeBackend) -> None:
    app = page()
    app.number_input(key="age").set_value(40).run()
    app.number_input(key="late_90").set_value(0).run()

    assert backend.recent_calls == 1
    assert backend.decisions == []


def test_the_page_says_when_the_recent_list_cannot_be_loaded(backend: FakeBackend) -> None:
    backend.recent_answer = Failure(FailureKind.NO_CONNECTION)

    app = page()

    assert app.warning[0].value == "The list of recent decisions could not be loaded."


def test_utilisation_is_asked_for_as_a_share_with_a_warning_above_one(
    backend: FakeBackend,
) -> None:
    app = page()
    field = app.number_input(key="revolving_utilisation")

    assert field.label == "Revolving utilisation (as a share, 0.30 is 30%)"
    field.set_value(30.0).run()
    assert app.warning[0].value == "That is above 1 (100%). Did you mean 0.30?"


def test_documents_of_different_people_keep_decide_disabled(backend: FakeBackend) -> None:
    app = fill_the_rest(page(EXTRACTION | {"same_applicant": False}))

    assert decide_button(app).disabled
    assert app.error[0].value == logic.SAME_APPLICANT_FALSE


def test_an_unchecked_applicant_is_said_and_does_not_block(backend: FakeBackend) -> None:
    app = fill_the_rest(page(EXTRACTION | {"same_applicant": None}))

    assert "could not be checked" in app.warning[0].value
    assert not decide_button(app).disabled


def test_unread_values_say_so_and_are_sent_as_null(backend: FakeBackend) -> None:
    unread = EXTRACTION | {
        "payslip": {"gross": None},
        "debt_register": {
            "has_loss_certificate": None,
            "applicant_name": None,
            "date_of_birth": None,
        },
    }
    app = fill_the_rest(page(unread))

    assert app.number_input(key="income_amount").value is None
    assert app.radio(key="loss_certificate").value is LossCertificate.NOT_READ
    assert all_text(app).count("could not be read") >= 4
    decide_button(app).click().run()

    (body,) = backend.decisions
    assert body["entered"]["monthly_income"] is None
    assert body["entered"]["has_loss_certificate"] is None


def test_a_case_worker_completes_a_decision(backend: FakeBackend) -> None:
    app = fill_the_rest(page(EXTRACTION))
    assert not decide_button(app).disabled

    decide_button(app).click().run()

    assert not app.exception
    (body,) = backend.decisions
    assert body["extraction_checkpoint"] == "model-b@abc123"
    assert body["entered"]["monthly_income"] == {
        "amount": "6000.00",
        "currency": "CHF",
        "period": "monthly",
    }
    assert body["entered"]["revolving_utilisation"] == 0.30
    text = all_text(app)
    assert "Outcome: refused" in [header.value for header in app.subheader]
    assert "41" in text
    assert "The loss certificate could not be read." in text
    assert logic.WORDING_LABEL in text
    assert "We cannot grant the credit at this time." in text
    # The list was loaded again after the decision and shows it at the top.
    assert backend.recent_calls == 2
    assert app.dataframe[0].value.iloc[0]["Decision"] == 41
    # Decide is enabled again once the answer is there.
    assert not decide_button(app).disabled


def test_without_a_sentence_there_is_no_label(backend: FakeBackend) -> None:
    backend.decision_answer = DECISION | {"wording": None}
    app = fill_the_rest(page(EXTRACTION))

    decide_button(app).click().run()

    assert logic.WORDING_LABEL not in all_text(app)
    assert "The loss certificate could not be read." in all_text(app)


def test_the_page_says_when_the_backend_does_not_answer(backend: FakeBackend) -> None:
    backend.decision_answer = Failure(FailureKind.NO_CONNECTION)
    app = fill_the_rest(page(EXTRACTION))

    decide_button(app).click().run()

    assert "The backend does not answer. Nothing was decided." in all_text(app)
    assert not decide_button(app).disabled


def test_reruns_after_a_decision_do_not_decide_again(backend: FakeBackend) -> None:
    app = fill_the_rest(page(EXTRACTION))
    decide_button(app).click().run()
    app.number_input(key="dependants").set_value(2).run()
    app.run()

    assert len(backend.decisions) == 1


def test_without_backend_url_the_page_says_so_and_calls_nothing(
    backend: FakeBackend, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("BACKEND_URL")

    app = AppTest.from_file(str(APP), default_timeout=30).run()

    assert "BACKEND_URL" in app.error[0].value
    assert backend.recent_calls == 0


@pytest.mark.parametrize("amount", [0.0, -100.0])
def test_an_income_of_zero_or_less_is_refused_and_nothing_is_sent(
    backend: FakeBackend, amount: float
) -> None:
    app = fill_the_rest(page(EXTRACTION))
    app.number_input(key="income_amount").set_value(amount).run()

    assert logic.INCOME_NOT_ABOVE_ZERO in [error.value for error in app.error]
    assert decide_button(app).disabled
    with pytest.raises(AppTestError, match="disabled"):
        decide_button(app).click()  # like a browser, AppTest cannot click a disabled button
    assert backend.decisions == []


def test_a_cleared_income_is_sent_as_null(backend: FakeBackend) -> None:
    app = fill_the_rest(page(EXTRACTION))
    app.number_input(key="income_amount").set_value(None).run()

    assert not decide_button(app).disabled
    decide_button(app).click().run()

    (body,) = backend.decisions
    assert body["entered"]["monthly_income"] is None


def test_a_slow_backend_is_not_reported_as_nothing_decided(backend: FakeBackend) -> None:
    backend.decision_answer = Failure(FailureKind.NO_ANSWER_IN_TIME)
    app = fill_the_rest(page(EXTRACTION))

    decide_button(app).click().run()

    text = all_text(app)
    assert logic.DECISION_NOT_IN_TIME in text
    assert "Nothing was decided" not in text
    # The list is loaded again, so the case worker can check it before deciding again.
    assert backend.recent_calls == 2


def test_an_approval_says_that_no_rule_failed(backend: FakeBackend) -> None:
    backend.decision_answer = DECISION | {"outcome": "approved", "reasons": [], "wording": None}
    app = fill_the_rest(page(EXTRACTION))

    decide_button(app).click().run()

    assert "Outcome: approved" in [header.value for header in app.subheader]
    assert "- No rule failed." in [element.value for element in app.markdown]
