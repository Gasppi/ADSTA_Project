"""What the Information Extraction Service answers. The backend holds a copy of these models."""

from __future__ import annotations

from datetime import date
from decimal import ROUND_HALF_UP, Decimal
from enum import StrEnum, auto
from typing import Final, Literal

from pydantic import BaseModel, ConfigDict

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

    def as_monthly(self) -> Money:
        if self.period is Period.MONTHLY:
            return self
        monthly = (self.amount / MONTHS_PER_YEAR).quantize(RAPPEN, rounding=ROUND_HALF_UP)
        return Money(amount=monthly, currency=self.currency, period=Period.MONTHLY)


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
    model_config = ConfigDict(frozen=True, use_attribute_docstrings=True)

    payslip: PayslipFields
    debt_register: RegisterExtractFields

    same_applicant: bool | None = None
    """Whether both documents name the same person, or None if it could not be checked."""

    checkpoint: str
    """The checkpoint and the revision of Model B that read the documents."""
