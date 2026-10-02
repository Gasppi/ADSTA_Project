"""The decision rules, and the limits they are applied against."""

from dataclasses import dataclass

from credit_backend.contracts import Outcome, Reason


@dataclass(frozen=True)
class Policy:
    threshold: float


@dataclass(frozen=True)
class RuleInputs:
    default_probability: float | None


@dataclass(frozen=True)
class Decision:
    outcome: Outcome
    reasons: tuple[Reason, ...]


def decide(inputs: RuleInputs, policy: Policy) -> Decision:
    """Every rule that fails adds its reason. No reason means approved."""
    reasons: list[Reason] = []

    if inputs.default_probability is not None and inputs.default_probability > policy.threshold:
        reasons.append(Reason.DEFAULT_PROBABILITY_ABOVE_THRESHOLD)

    outcome = Outcome.REFUSED if reasons else Outcome.APPROVED
    return Decision(outcome=outcome, reasons=tuple(reasons))
