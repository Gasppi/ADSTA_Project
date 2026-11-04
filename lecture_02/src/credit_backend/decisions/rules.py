"""The decision rules, and the limits they are applied against."""

from dataclasses import dataclass

from credit_backend.contracts import Money, Outcome, Reason


@dataclass(frozen=True)
class Policy:
    threshold: float


@dataclass(frozen=True)
class RuleInputs:
    default_probability: float | None
    monthly_income: Money | None
    """The income as the case worker confirmed it, or None if nobody could establish it."""
    has_loss_certificate: bool | None
    """True when the register records an open loss certificate, None when nobody could read it."""


@dataclass(frozen=True)
class Decision:
    outcome: Outcome
    reasons: tuple[Reason, ...]


def decide(inputs: RuleInputs, policy: Policy) -> Decision:
    """Every rule that fails adds its reason. No reason means approved."""
    reasons: list[Reason] = []

    if inputs.default_probability is not None and inputs.default_probability >= policy.threshold:
        reasons.append(Reason.DEFAULT_PROBABILITY_ABOVE_THRESHOLD)

    if inputs.has_loss_certificate is None:
        reasons.append(Reason.LOSS_CERTIFICATE_UNKNOWN)
    elif inputs.has_loss_certificate:
        reasons.append(Reason.LOSS_CERTIFICATE_OPEN)

    if inputs.monthly_income is None:
        reasons.append(Reason.INCOME_UNKNOWN)

    outcome = Outcome.REFUSED if reasons else Outcome.APPROVED
    return Decision(outcome=outcome, reasons=tuple(reasons))
