from decimal import Decimal
from typing import Final

import pytest

from credit_backend.contracts import Money, Outcome, Period, Reason
from credit_backend.decisions.rules import Policy, RuleInputs, decide

POLICY: Final = Policy(threshold=0.30)
INCOME: Final = Money(amount=Decimal("6000.00"), currency="CHF", period=Period.MONTHLY)


def inputs(
    default_probability: float | None = 0.10,
    monthly_income: Money | None = INCOME,
    has_loss_certificate: bool | None = False,
) -> RuleInputs:
    return RuleInputs(
        default_probability=default_probability,
        monthly_income=monthly_income,
        has_loss_certificate=has_loss_certificate,
    )


def test_a_sound_application_is_approved() -> None:
    assert decide(inputs(default_probability=0.05), POLICY).outcome is Outcome.APPROVED


@pytest.mark.parametrize(
    ("probability", "outcome"),
    [(0.29, Outcome.APPROVED), (0.30, Outcome.REFUSED), (0.31, Outcome.REFUSED)],
)
def test_threshold_boundary(probability: float, outcome: Outcome) -> None:
    assert decide(inputs(default_probability=probability), POLICY).outcome is outcome


def test_an_application_at_the_threshold_is_refused_with_its_reason() -> None:
    decision = decide(inputs(default_probability=POLICY.threshold), POLICY)

    assert decision.outcome is Outcome.REFUSED
    assert Reason.DEFAULT_PROBABILITY_ABOVE_THRESHOLD in decision.reasons


def test_an_open_loss_certificate_refuses_the_application() -> None:
    decision = decide(inputs(has_loss_certificate=True), POLICY)

    assert decision.outcome is Outcome.REFUSED
    assert Reason.LOSS_CERTIFICATE_OPEN in decision.reasons


def test_a_register_nobody_could_read_is_not_taken_for_a_clean_one() -> None:
    unread = decide(inputs(has_loss_certificate=None), POLICY)
    clean = decide(inputs(has_loss_certificate=False), POLICY)

    assert clean.outcome is Outcome.APPROVED
    assert unread.outcome is Outcome.REFUSED
    assert Reason.LOSS_CERTIFICATE_UNKNOWN in unread.reasons


def test_an_income_nobody_could_read_gets_a_reason_of_its_own() -> None:
    unread = decide(inputs(monthly_income=None), POLICY)
    read = decide(inputs(), POLICY)

    assert read.outcome is Outcome.APPROVED
    assert Reason.INCOME_UNKNOWN in unread.reasons
