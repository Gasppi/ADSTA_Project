"""What a request to the backend carries, and what the backend answers."""

from datetime import date, datetime
from decimal import ROUND_HALF_UP, Decimal
from enum import StrEnum, auto
from typing import Final, Literal

from pydantic import BaseModel, ConfigDict, Field, JsonValue

MONTHS_PER_YEAR: Final = 12
RAPPEN: Final = Decimal("0.01")


class Period(StrEnum):
    MONTHLY = auto()
    ANNUAL = auto()


class Money(BaseModel):
    """An amount that carries the period it is expressed in."""

    model_config = ConfigDict(frozen=True)

    amount: Decimal
    currency: Literal["CHF"]
    period: Period

    def as_monthly(self) -> "Money":
        if self.period is Period.MONTHLY:
            return self
        monthly = (self.amount / MONTHS_PER_YEAR).quantize(RAPPEN, rounding=ROUND_HALF_UP)
        return Money(amount=monthly, currency=self.currency, period=Period.MONTHLY)


class Outcome(StrEnum):
    APPROVED = auto()
    REFUSED = auto()


class Reason(StrEnum):
    """The facts a decision rests on, before anybody puts them into words."""

    DEFAULT_PROBABILITY_ABOVE_THRESHOLD = auto()
    LOSS_CERTIFICATE_OPEN = auto()
    LOSS_CERTIFICATE_UNKNOWN = auto()
    INCOME_UNKNOWN = auto()


class CaseWorkerInput(BaseModel):
    """The application as the case worker entered it."""

    model_config = ConfigDict(frozen=True, use_attribute_docstrings=True)

    age: int = Field(ge=18, le=120)
    dependants: int = Field(ge=0)
    open_credit_lines: int = Field(ge=0)
    real_estate_lines: int = Field(ge=0)
    late_30_59: int = Field(ge=0)
    """Payments between 30 and 59 days late."""
    late_60_89: int = Field(ge=0)
    """Payments between 60 and 89 days late."""
    late_90: int = Field(ge=0)
    """Payments 90 or more days late."""
    revolving_utilisation: float = Field(ge=0.0)
    """The share of available revolving credit in use."""
    monthly_debt_obligations: Decimal = Field(ge=0)
    """What the applicant already pays each month towards debts, in CHF."""

    monthly_income: Money | None = None
    """The income, or None if it could not be established."""

    has_loss_certificate: bool | None = None
    """Whether the register records an open loss certificate, or None if nobody could read it."""


SAMPLE_REQUEST: Final[dict[str, JsonValue]] = {
    "entered": {
        "age": 34,
        "dependants": 1,
        "open_credit_lines": 3,
        "real_estate_lines": 0,
        "late_30_59": 0,
        "late_60_89": 0,
        "late_90": 0,
        "revolving_utilisation": 0.25,
        "monthly_debt_obligations": "1200.00",
        "monthly_income": {"amount": "6000.00", "currency": "CHF", "period": "monthly"},
        "has_loss_certificate": False,
    },
}


class DecisionRequest(BaseModel):
    """The application a case worker has confirmed, sent for a decision."""

    model_config = ConfigDict(frozen=True, json_schema_extra={"examples": [SAMPLE_REQUEST]})

    entered: CaseWorkerInput

    extraction_checkpoint: str | None = None
    """The Model B that read the documents the figures were confirmed against, if any."""


class DecisionResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    outcome: Outcome
    reasons: list[Reason]
    wording: str | None
    features: dict[str, float | None]
    default_probability: float | None
    model_version: str
    record_id: int


class DecisionRecordRead(BaseModel):
    """One stored decision, as GET /decisions/recent shows it."""

    model_config = ConfigDict(frozen=True, from_attributes=True)

    id: int
    created_at: datetime
    age: float | None
    dependents: float | None
    rev_util: float | None
    late_90: float | None
    monthly_inc: float | None
    debt_ratio: float | None
    has_loss_certificate: bool | None
    extraction_checkpoint: str | None
    default_probability: float | None
    model_version: str
    outcome: Outcome
    reasons: list[Reason]
    wording: str | None


class PayslipFields(BaseModel):
    """What the payslip said, or None where it could not be read."""

    model_config = ConfigDict(frozen=True, use_attribute_docstrings=True)

    gross: Money | None
    """The gross monthly salary, or None if unread."""


class RegisterExtractFields(BaseModel):
    """What the register extract said, or None where it could not be read."""

    model_config = ConfigDict(frozen=True, use_attribute_docstrings=True)

    has_loss_certificate: bool | None = None
    """Whether the extract records a loss certificate, or None if unread."""

    applicant_name: str | None = None
    """The person the extract is made out to, or None if unread."""

    date_of_birth: date | None = None
    """The applicant's date of birth, or None if unread."""


class ExtractionResult(BaseModel):
    """What the Information Extraction Service read, before a case worker confirms it."""

    model_config = ConfigDict(frozen=True, use_attribute_docstrings=True)

    payslip: PayslipFields
    debt_register: RegisterExtractFields

    same_applicant: bool | None = None
    """Whether both documents name the same person, or None if it could not be checked."""

    checkpoint: str
    """The checkpoint and the revision of Model B that read the documents."""
