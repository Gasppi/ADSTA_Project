"""The application is checked when it arrives, before anything is decided."""

import pytest
from pydantic import ValidationError

from credit_backend.contracts import CaseWorkerInput


def application(income: dict[str, str] | None) -> CaseWorkerInput:
    return CaseWorkerInput(
        age=34,
        dependants=1,
        open_credit_lines=3,
        real_estate_lines=0,
        late_30_59=0,
        late_60_89=0,
        late_90=0,
        revolving_utilisation=0.25,
        monthly_debt_obligations="1200.00",
        monthly_income=income,
    )


@pytest.mark.parametrize(
    ("amount", "period"),
    [("0.00", "monthly"), ("0", "annual"), ("0.05", "annual"), ("-100", "monthly")],
)
def test_an_income_of_zero_or_less_is_refused(amount: str, period: str) -> None:
    income = {"amount": amount, "currency": "CHF", "period": period}

    with pytest.raises(ValidationError, match="above 0"):
        application(income)


@pytest.mark.parametrize(("amount", "period"), [("6000.00", "monthly"), ("0.12", "annual")])
def test_an_income_above_zero_is_accepted(amount: str, period: str) -> None:
    income = {"amount": amount, "currency": "CHF", "period": period}

    assert application(income).monthly_income is not None


def test_an_income_nobody_could_establish_is_still_accepted() -> None:
    assert application(None).monthly_income is None
