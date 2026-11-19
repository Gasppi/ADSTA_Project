"""What the page does, apart from the Streamlit calls, so that tests can call it.

The page never decides. Nothing here scores an application or compares a number against a
limit. The backend decides, and this module only builds what is sent and words what comes back.
"""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from enum import StrEnum
from typing import Any, Final

from credit_frontend.backend import Failure, FailureKind

# --- Texts from the specification ----------------------------------------------------------

NOT_READ: Final = "could not be read"
WORDING_LABEL: Final = "Written by a model and not checked by a person."

NO_CONNECTION: Final = "The backend does not answer. Nothing was decided."
DECISION_NOT_IN_TIME: Final = (
    "The backend did not answer in time. The decision may still have been recorded. "
    "Check the list of recent decisions before deciding again."
)
EXTRACTION_NOT_IN_TIME: Final = (
    "The backend did not answer in time. Nothing was decided. Try again."
)
FIELD_DOES_NOT_FIT: Final = "A field is missing or does not fit."
EXTRACTION_NO_RESULT: Final = (
    "The extraction service gave no result. It may be down, or it may have rejected a document. "
    "Try again later or check the documents. Nothing can be decided without the documents."
)
DECISION_FAILED: Final = (
    "The backend failed and returned no decision. "
    "Check the list of recent decisions before deciding again."
)
# The specification names no sentence for an answer to POST /extractions other than 200, 422
# and 503. POST /extractions never decides, so this sentence is true for all of them.
EXTRACTION_FAILED: Final = "The backend failed. Nothing was decided."
NO_RULE_FAILED: Final = "No rule failed."
INCOME_NOT_ABOVE_ZERO: Final = (
    "The income must be above 0. Leave the field empty if nobody could establish it."
)
RECENT_NOT_LOADED: Final = "The list of recent decisions could not be loaded."
NO_DECISIONS: Final = "No decisions yet."

SAME_APPLICANT_FALSE: Final = (
    "The documents name different people. Upload other documents to decide."
)
SAME_APPLICANT_NULL: Final = "Whether both documents name the same person could not be checked."
SAME_APPLICANT_TRUE: Final = "Both documents name the same person."

REASON_TEXTS: Final[Mapping[str, str]] = {
    "default_probability_above_threshold": (
        "The estimated probability of default is above the bank's limit."
    ),
    "loss_certificate_open": "The register shows an open loss certificate.",
    "loss_certificate_unknown": "The loss certificate could not be read.",
    "income_unknown": "The income could not be established.",
}

UTILISATION_LABEL: Final = "Revolving utilisation (as a share, 0.30 is 30%)"

FIELD_LABELS: Final[Mapping[str, str]] = {
    "age": "Age",
    "dependants": "Dependants",
    "open_credit_lines": "Open credit lines",
    "real_estate_lines": "Real estate lines",
    "late_30_59": "Payments 30 to 59 days late",
    "late_60_89": "Payments 60 to 89 days late",
    "late_90": "Payments 90 or more days late",
    "revolving_utilisation": UTILISATION_LABEL,
    "monthly_debt_obligations": "Monthly debt obligations (CHF per month)",
    "monthly_income": "Gross income (CHF)",
    "income_period": "Period of the income",
    "has_loss_certificate": "Loss certificate",
    "payslip": "Payslip",
    "debt_register": "Debt register extract",
    "extraction_checkpoint": "Checkpoint of the extraction",
}

# The fields the case worker must fill, in the order of the page.
REQUIRED_INTEGERS: Final = (
    "age",
    "dependants",
    "open_credit_lines",
    "real_estate_lines",
    "late_30_59",
    "late_60_89",
    "late_90",
)


# --- The values on the screen ------------------------------------------------------------


class LossCertificate(StrEnum):
    """The three choices. None of them is preselected before the documents are read."""

    NONE_RECORDED = "none recorded"
    RECORDED = "recorded"
    NOT_READ = NOT_READ


LOSS_CERTIFICATE_VALUES: Final[Mapping[LossCertificate, bool | None]] = {
    LossCertificate.NONE_RECORDED: False,
    LossCertificate.RECORDED: True,
    LossCertificate.NOT_READ: None,
}

PERIODS: Final = ("monthly", "annual")


def loss_certificate_choice(read: bool | None) -> LossCertificate:
    """The choice that shows what the register extract said."""
    if read is None:
        return LossCertificate.NOT_READ
    return LossCertificate.RECORDED if read else LossCertificate.NONE_RECORDED


@dataclass(frozen=True)
class EnteredValues:
    """The values on the screen, as Streamlit gives them. None means the field is empty."""

    age: int | None = None
    dependants: int | None = None
    open_credit_lines: int | None = None
    real_estate_lines: int | None = None
    late_30_59: int | None = None
    late_60_89: int | None = None
    late_90: int | None = None
    revolving_utilisation: float | None = None
    monthly_debt_obligations: float | None = None
    income_amount: float | None = None
    income_period: str | None = None
    loss_certificate: LossCertificate | None = None


def missing_fields(values: EnteredValues) -> list[str]:
    """The fields that still need a value before Decide can be pressed, as their labels.

    An empty income is not missing: it means nobody could establish the income and is sent
    as null. Only a period is needed once an amount was entered.
    """
    names = [name for name in REQUIRED_INTEGERS if getattr(values, name) is None]
    if values.revolving_utilisation is None:
        names.append("revolving_utilisation")
    if values.monthly_debt_obligations is None:
        names.append("monthly_debt_obligations")
    if values.income_amount is not None and values.income_period not in PERIODS:
        names.append("income_period")
    if values.loss_certificate is None:
        names.append("has_loss_certificate")
    return [FIELD_LABELS[name] for name in names]


class IncompleteError(ValueError):
    """The values cannot be sent yet."""


def _chf(amount: float) -> str:
    """A decimal string with two places, as the backend's Decimal and Money expect."""
    return f"{Decimal(str(amount)):.2f}"


def income_problem(amount: float | None) -> str | None:
    """Why the income cannot be sent, or None if it can.

    An empty field is fine: it is sent as null. An amount must be above 0 as it is sent, with
    two places, so 0.004 (sent as 0.00) is refused like 0. The page does not convert an annual
    amount to a monthly one; the backend rejects a monthly amount of 0 or less with a 422.
    """
    if amount is None:
        return None
    if Decimal(_chf(amount)) <= 0:
        return INCOME_NOT_ABOVE_ZERO
    return None


def build_decision_body(values: EnteredValues, checkpoint: str) -> dict[str, Any]:
    """The JSON body of POST /decisions.

    An unread value is sent as null, never as 0 or false. Utilisation is sent as the share the
    case worker typed, with no conversion.
    """
    missing = missing_fields(values)
    if missing:
        raise IncompleteError(f"Fill in: {', '.join(missing)}.")
    problem = income_problem(values.income_amount)
    if problem:
        raise IncompleteError(problem)
    if values.monthly_debt_obligations is not None and values.monthly_debt_obligations < 0:
        raise IncompleteError("The monthly debt obligations cannot be negative.")

    # missing_fields() has made sure that none of these is None.
    assert values.revolving_utilisation is not None
    assert values.monthly_debt_obligations is not None
    assert values.loss_certificate is not None

    income = None
    if values.income_amount is not None:
        income = {
            "amount": _chf(values.income_amount),
            "currency": "CHF",
            "period": values.income_period,
        }
    entered: dict[str, Any] = {name: getattr(values, name) for name in REQUIRED_INTEGERS}
    entered |= {
        "revolving_utilisation": values.revolving_utilisation,
        "monthly_debt_obligations": _chf(values.monthly_debt_obligations),
        "monthly_income": income,
        "has_loss_certificate": LOSS_CERTIFICATE_VALUES[values.loss_certificate],
    }
    return {"entered": entered, "extraction_checkpoint": checkpoint}


def utilisation_warning(share: float | None) -> str | None:
    """A soft warning above 1 (100%). The value is still allowed and sent as typed."""
    if share is None or share <= 1:
        return None
    suggestion = Decimal(str(share)) / 100
    exponent = suggestion.normalize().as_tuple().exponent
    places = max(2, -exponent) if isinstance(exponent, int) else 2
    return f"That is above 1 (100%). Did you mean {suggestion:.{places}f}?"


# --- The gate in front of Decide -----------------------------------------------------------


def decide_blockers(
    *,
    extraction: Mapping[str, Any] | None,
    values: EnteredValues,
    deciding: bool,
) -> list[str]:
    """Why Decide is disabled. An empty list means it is enabled."""
    if deciding:
        return ["A decision is running."]
    if extraction is None:
        return ["Upload both documents and wait until they were read."]
    blockers = []
    if extraction.get("same_applicant") is False:
        blockers.append(SAME_APPLICANT_FALSE)
    missing = missing_fields(values)
    if missing:
        blockers.append(f"Fill in: {', '.join(missing)}.")
    problem = income_problem(values.income_amount)
    if problem:
        blockers.append(problem)
    return blockers


def same_applicant_text(same_applicant: bool | None) -> str:
    if same_applicant is None:
        return SAME_APPLICANT_NULL
    return SAME_APPLICANT_TRUE if same_applicant else SAME_APPLICANT_FALSE


# --- Words for what came back --------------------------------------------------------------


def reason_text(code: str) -> str:
    """The plain words for a reason code. An unknown code is shown as it came."""
    return REASON_TEXTS.get(code, code)


def reason_texts(codes: Sequence[str]) -> list[str]:
    """The reasons in words. An approval has no reasons, and then no rule failed."""
    if not codes:
        return [NO_RULE_FAILED]
    return [reason_text(code) for code in codes]


def wording_to_show(decision: Mapping[str, Any]) -> str | None:
    """Model C's sentence, or None when there is none to show (and so no label either)."""
    wording = decision.get("wording")
    if not isinstance(wording, str) or not wording.strip():
        return None
    return wording


def fields_from_detail(detail: Any) -> list[str]:
    """The labels of the fields named in a FastAPI 422 `detail`, in order, without repeats."""
    if not isinstance(detail, list):
        return []
    labels: list[str] = []
    for error in detail:
        location = error.get("loc") if isinstance(error, dict) else None
        if not isinstance(location, list):
            continue
        names = [str(part) for part in location if part not in ("body", "entered")]
        if not names:
            continue
        label = FIELD_LABELS.get(names[0], names[0])
        if label not in labels:
            labels.append(label)
    return labels


def _field_sentence(detail: Any) -> str:
    labels = fields_from_detail(detail)
    if not labels:
        return FIELD_DOES_NOT_FIT
    return f"{FIELD_DOES_NOT_FIT} Field: {', '.join(labels)}."


def extraction_failure_text(failure: Failure) -> str:
    """The sentence for a failed POST /extractions."""
    if failure.kind is FailureKind.NO_CONNECTION:
        return NO_CONNECTION
    if failure.kind is FailureKind.NO_ANSWER_IN_TIME:
        return EXTRACTION_NOT_IN_TIME
    if failure.status_code == 422:
        return _field_sentence(failure.detail)
    if failure.status_code == 503:
        return EXTRACTION_NO_RESULT
    return EXTRACTION_FAILED


def decision_failure_text(failure: Failure) -> str:
    """The sentence for a failed POST /decisions.

    Only a refused connection says that nothing was decided. Every other failure may come after
    the backend stored the decision, so it points to the list of recent decisions.
    """
    if failure.kind is FailureKind.NO_CONNECTION:
        return NO_CONNECTION
    if failure.kind is FailureKind.NO_ANSWER_IN_TIME:
        return DECISION_NOT_IN_TIME
    if failure.status_code == 422:
        return _field_sentence(failure.detail)
    # Any 5xx, and also any status or answer the specification does not name.
    return DECISION_FAILED


def format_money(money: Mapping[str, Any] | None) -> str:
    if money is None:
        return NOT_READ
    return f"{money.get('amount')} {money.get('currency')} {money.get('period')}"


def read_income_amount(money: Mapping[str, Any] | None) -> float | None:
    """The amount that was read, for the income field. None leaves the field empty."""
    if money is None:
        return None
    try:
        return float(Decimal(str(money["amount"])))
    except (KeyError, InvalidOperation, ValueError):
        return None


def format_time(created_at: Any) -> str:
    try:
        moment = datetime.fromisoformat(str(created_at))
    except ValueError:
        return str(created_at)
    if moment.tzinfo is not None:
        moment = moment.astimezone(UTC)
        return moment.strftime("%Y-%m-%d %H:%M:%S UTC")
    return moment.strftime("%Y-%m-%d %H:%M:%S")


def recent_rows(records: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    """The rows of the recent list, in the order the backend sent them (newest first).

    The backend already sorts newest first, and the specification says the page keeps that
    order, so this function does not sort again.
    """
    return [
        {
            "Decision": record.get("id"),
            "Time": format_time(record.get("created_at")),
            "Outcome": record.get("outcome"),
            "Reasons": " ".join(reason_texts(record.get("reasons") or [])),
        }
        for record in records
    ]
