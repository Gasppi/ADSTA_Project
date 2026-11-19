from dataclasses import replace

import pytest

from credit_frontend import logic
from credit_frontend.backend import Failure, FailureKind
from credit_frontend.logic import EnteredValues, LossCertificate

COMPLETE = EnteredValues(
    age=34,
    dependants=1,
    open_credit_lines=3,
    real_estate_lines=0,
    late_30_59=0,
    late_60_89=0,
    late_90=0,
    revolving_utilisation=0.30,
    monthly_debt_obligations=1200.0,
    income_amount=6000.0,
    income_period="monthly",
    loss_certificate=LossCertificate.NONE_RECORDED,
)
EXTRACTION = {
    "payslip": {"gross": {"amount": "6000.00", "currency": "CHF", "period": "monthly"}},
    "debt_register": {"has_loss_certificate": False},
    "same_applicant": True,
    "checkpoint": "model-b@abc123",
}


# --- The request body ---------------------------------------------------------------------


def test_a_complete_application_becomes_the_body_of_the_contract() -> None:
    body = logic.build_decision_body(COMPLETE, "model-b@abc123")

    assert body == {
        "entered": {
            "age": 34,
            "dependants": 1,
            "open_credit_lines": 3,
            "real_estate_lines": 0,
            "late_30_59": 0,
            "late_60_89": 0,
            "late_90": 0,
            "revolving_utilisation": 0.30,
            "monthly_debt_obligations": "1200.00",
            "monthly_income": {"amount": "6000.00", "currency": "CHF", "period": "monthly"},
            "has_loss_certificate": False,
        },
        "extraction_checkpoint": "model-b@abc123",
    }


def test_income_carries_the_period_on_the_screen() -> None:
    values = replace(COMPLETE, income_amount=72000.5, income_period="annual")

    income = logic.build_decision_body(values, "c")["entered"]["monthly_income"]

    assert income == {"amount": "72000.50", "currency": "CHF", "period": "annual"}


def test_an_empty_income_is_sent_as_null_and_never_as_zero() -> None:
    values = replace(COMPLETE, income_amount=None, income_period=None)

    entered = logic.build_decision_body(values, "c")["entered"]

    assert entered["monthly_income"] is None


def test_a_cleared_income_is_null_even_if_a_period_is_still_chosen() -> None:
    values = replace(COMPLETE, income_amount=None, income_period="monthly")

    assert logic.build_decision_body(values, "c")["entered"]["monthly_income"] is None


@pytest.mark.parametrize(
    ("choice", "sent"),
    [
        (LossCertificate.NONE_RECORDED, False),
        (LossCertificate.RECORDED, True),
        (LossCertificate.NOT_READ, None),
    ],
)
def test_the_three_loss_certificate_choices(choice: LossCertificate, sent: bool | None) -> None:
    values = replace(COMPLETE, loss_certificate=choice)

    assert logic.build_decision_body(values, "c")["entered"]["has_loss_certificate"] is sent


def test_utilisation_is_sent_as_the_share_that_was_typed() -> None:
    for share in (0.30, 30.0):
        values = replace(COMPLETE, revolving_utilisation=share)
        assert logic.build_decision_body(values, "c")["entered"]["revolving_utilisation"] == share


@pytest.mark.parametrize("name", [*logic.REQUIRED_INTEGERS, "revolving_utilisation"])
def test_an_empty_required_field_is_never_sent(name: str) -> None:
    values = replace(COMPLETE, **{name: None})

    with pytest.raises(logic.IncompleteError):
        logic.build_decision_body(values, "c")


def test_an_empty_debt_obligation_is_never_sent_as_zero() -> None:
    values = replace(COMPLETE, monthly_debt_obligations=None)

    with pytest.raises(logic.IncompleteError):
        logic.build_decision_body(values, "c")


def test_zero_that_was_typed_is_sent_as_zero() -> None:
    entered = logic.build_decision_body(replace(COMPLETE, dependants=0), "c")["entered"]

    assert entered["dependants"] == 0


def test_no_choice_for_the_loss_certificate_is_not_sent() -> None:
    with pytest.raises(logic.IncompleteError):
        logic.build_decision_body(replace(COMPLETE, loss_certificate=None), "c")


def test_an_amount_without_a_period_is_not_sent() -> None:
    with pytest.raises(logic.IncompleteError):
        logic.build_decision_body(replace(COMPLETE, income_period=None), "c")


@pytest.mark.parametrize("amount", [0.0, -100.0, -0.01, 0.004])
def test_an_income_of_zero_or_less_is_refused_and_never_sent(amount: float) -> None:
    # 0.004 would be sent as "0.00", so it is refused like 0.
    values = replace(COMPLETE, income_amount=amount)

    with pytest.raises(logic.IncompleteError, match="must be above 0"):
        logic.build_decision_body(values, "c")
    assert logic.income_problem(amount) == logic.INCOME_NOT_ABOVE_ZERO
    assert logic.INCOME_NOT_ABOVE_ZERO in logic.decide_blockers(
        extraction=EXTRACTION, values=values, deciding=False
    )


@pytest.mark.parametrize("amount", [None, 0.01, 6000.0])
def test_an_empty_income_or_one_above_zero_is_accepted(amount: float | None) -> None:
    assert logic.income_problem(amount) is None


def test_missing_fields_are_named_by_their_labels() -> None:
    missing = logic.missing_fields(EnteredValues())

    assert logic.FIELD_LABELS["age"] in missing
    assert logic.UTILISATION_LABEL in missing
    assert logic.FIELD_LABELS["has_loss_certificate"] in missing
    # An empty income is an answer (unknown), not a missing field.
    assert logic.FIELD_LABELS["monthly_income"] not in missing
    assert logic.FIELD_LABELS["income_period"] not in missing


# --- Utilisation warning ------------------------------------------------------------------


@pytest.mark.parametrize("share", [None, 0.0, 0.30, 1.0])
def test_no_warning_up_to_one(share: float | None) -> None:
    assert logic.utilisation_warning(share) is None


def test_a_share_above_one_gets_the_warning_of_the_specification() -> None:
    assert logic.utilisation_warning(30) == "That is above 1 (100%). Did you mean 0.30?"


def test_the_warning_suggests_the_share_of_what_was_typed() -> None:
    assert logic.utilisation_warning(45.0) == "That is above 1 (100%). Did you mean 0.45?"
    assert logic.utilisation_warning(1.5) == "That is above 1 (100%). Did you mean 0.015?"


# --- The gate in front of Decide ----------------------------------------------------------


def test_decide_is_disabled_before_the_documents_were_read() -> None:
    assert logic.decide_blockers(extraction=None, values=COMPLETE, deciding=False)


def test_decide_is_enabled_with_read_documents_and_every_field() -> None:
    assert logic.decide_blockers(extraction=EXTRACTION, values=COMPLETE, deciding=False) == []


def test_decide_is_disabled_while_a_decision_is_running() -> None:
    assert logic.decide_blockers(extraction=EXTRACTION, values=COMPLETE, deciding=True)


def test_decide_is_disabled_until_every_required_field_has_a_value() -> None:
    blockers = logic.decide_blockers(
        extraction=EXTRACTION, values=replace(COMPLETE, age=None), deciding=False
    )

    assert blockers == [f"Fill in: {logic.FIELD_LABELS['age']}."]


def test_documents_of_different_people_block_the_decision() -> None:
    extraction = EXTRACTION | {"same_applicant": False}

    blockers = logic.decide_blockers(extraction=extraction, values=COMPLETE, deciding=False)

    assert blockers == [logic.SAME_APPLICANT_FALSE]


def test_an_unchecked_applicant_does_not_block() -> None:
    extraction = EXTRACTION | {"same_applicant": None}

    assert logic.decide_blockers(extraction=extraction, values=COMPLETE, deciding=False) == []
    assert "could not be checked" in logic.same_applicant_text(None)


# --- What was read ------------------------------------------------------------------------


def test_read_values_fill_the_fields_and_unread_values_leave_them_empty() -> None:
    assert logic.read_income_amount({"amount": "6000.00", "period": "monthly"}) == 6000.0
    assert logic.read_income_amount(None) is None
    assert logic.loss_certificate_choice(True) is LossCertificate.RECORDED
    assert logic.loss_certificate_choice(False) is LossCertificate.NONE_RECORDED
    assert logic.loss_certificate_choice(None) is LossCertificate.NOT_READ
    assert logic.format_money(None) == "could not be read"


# --- Words for what came back -------------------------------------------------------------


def test_every_reason_code_has_the_text_of_the_specification() -> None:
    assert logic.reason_texts(
        [
            "default_probability_above_threshold",
            "loss_certificate_open",
            "loss_certificate_unknown",
            "income_unknown",
        ]
    ) == [
        "The estimated probability of default is above the bank's limit.",
        "The register shows an open loss certificate.",
        "The loss certificate could not be read.",
        "The income could not be established.",
    ]


def test_an_approval_without_reasons_says_that_no_rule_failed() -> None:
    assert logic.reason_texts([]) == ["No rule failed."]


def test_an_unknown_reason_code_is_shown_as_it_came() -> None:
    assert logic.reason_text("something_new") == "something_new"


def test_the_sentence_of_model_c_is_shown_only_when_there_is_one() -> None:
    assert logic.wording_to_show({"wording": "Your application was approved."}) == (
        "Your application was approved."
    )
    assert logic.wording_to_show({"wording": None}) is None
    assert logic.wording_to_show({"wording": "  "}) is None


NO_CONNECTION = Failure(FailureKind.NO_CONNECTION)
NOT_IN_TIME = Failure(FailureKind.NO_ANSWER_IN_TIME)
DETAIL_422 = [
    {"loc": ["body", "entered", "age"], "msg": "Input should be >= 18", "type": "x"},
    {"loc": ["body", "entered", "monthly_income"], "msg": "must be above 0", "type": "x"},
    {"loc": ["body", "entered", "age"], "msg": "repeat", "type": "x"},
]
DECISION_FAILED = (
    "The backend failed and returned no decision. "
    "Check the list of recent decisions before deciding again."
)


@pytest.mark.parametrize(
    ("failure", "sentence"),
    [
        (NO_CONNECTION, "The backend does not answer. Nothing was decided."),
        (NOT_IN_TIME, "The backend did not answer in time. Nothing was decided. Try again."),
        (
            Failure(FailureKind.STATUS, 503, "The Information Extraction Service ..."),
            "The extraction service gave no result. It may be down, or it may have rejected a "
            "document. Try again later or check the documents. Nothing can be decided without "
            "the documents.",
        ),
        (
            Failure(FailureKind.STATUS, 422, [{"loc": ["body", "payslip"], "msg": "Field"}]),
            "A field is missing or does not fit. Field: Payslip.",
        ),
        (Failure(FailureKind.STATUS, 500), "The backend failed. Nothing was decided."),
        (Failure(FailureKind.INVALID_ANSWER, 200), "The backend failed. Nothing was decided."),
    ],
)
def test_each_failure_of_the_extraction_has_its_sentence(failure: Failure, sentence: str) -> None:
    assert logic.extraction_failure_text(failure) == sentence


@pytest.mark.parametrize(
    ("failure", "sentence"),
    [
        (NO_CONNECTION, "The backend does not answer. Nothing was decided."),
        (
            NOT_IN_TIME,
            "The backend did not answer in time. The decision may still have been recorded. "
            "Check the list of recent decisions before deciding again.",
        ),
        (
            Failure(FailureKind.STATUS, 422, DETAIL_422),
            "A field is missing or does not fit. Field: Age, Gross income (CHF).",
        ),
        (Failure(FailureKind.STATUS, 422, "not a list"), "A field is missing or does not fit."),
        (Failure(FailureKind.STATUS, 500), DECISION_FAILED),
        (Failure(FailureKind.STATUS, 502), DECISION_FAILED),
        (Failure(FailureKind.STATUS, 503), DECISION_FAILED),
        (Failure(FailureKind.STATUS, 504), DECISION_FAILED),
        (Failure(FailureKind.INVALID_ANSWER, 200), DECISION_FAILED),
    ],
)
def test_each_failure_of_a_decision_has_its_sentence(failure: Failure, sentence: str) -> None:
    assert logic.decision_failure_text(failure) == sentence


def test_only_a_refused_connection_says_that_nothing_was_decided() -> None:
    failures = [NOT_IN_TIME, Failure(FailureKind.STATUS, 500), Failure(FailureKind.STATUS, 503)]

    for failure in failures:
        assert "Nothing was decided" not in logic.decision_failure_text(failure)


# --- The recent list ----------------------------------------------------------------------


def test_the_recent_list_keeps_the_order_of_the_backend() -> None:
    records = [
        {
            "id": 7,
            "created_at": "2026-11-19T14:03:05.123456Z",
            "outcome": "refused",
            "reasons": ["income_unknown", "loss_certificate_open"],
        },
        {"id": 9, "created_at": "2026-11-19T15:00:00+01:00", "outcome": "approved", "reasons": []},
        {"id": 3, "created_at": "not a time", "outcome": "approved", "reasons": []},
    ]

    rows = logic.recent_rows(records)

    assert [row["Decision"] for row in rows] == [7, 9, 3]
    assert rows[0] == {
        "Decision": 7,
        "Time": "2026-11-19 14:03:05 UTC",
        "Outcome": "refused",
        "Reasons": "The income could not be established. "
        "The register shows an open loss certificate.",
    }
    assert rows[1]["Time"] == "2026-11-19 14:00:00 UTC"
    assert rows[1]["Reasons"] == "No rule failed."
    assert rows[2]["Time"] == "not a time"


def test_an_empty_recent_list_has_no_rows() -> None:
    assert logic.recent_rows([]) == []
