"""What a request to the backend carries, and what the backend answers."""

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
    },
}


class DecisionRequest(BaseModel):
    """The application a case worker has confirmed, sent for a decision."""

    model_config = ConfigDict(frozen=True, json_schema_extra={"examples": [SAMPLE_REQUEST]})

    entered: CaseWorkerInput


class DecisionResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    outcome: Outcome
    reasons: list[Reason]
    features: dict[str, float | None]
    default_probability: float | None
    model_version: str
