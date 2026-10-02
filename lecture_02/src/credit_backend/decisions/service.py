"""One decision, from the confirmed application to the answer."""

from dataclasses import asdict
from decimal import Decimal

from credit_backend.contracts import DecisionRequest, DecisionResponse
from credit_backend.decisions.features import build_features
from credit_backend.decisions.rules import Policy, RuleInputs, decide
from credit_backend.decisions.scoring import Scorer


class DecisionService:
    def __init__(self, scorer: Scorer, policy: Policy) -> None:
        self._scorer = scorer
        self._policy = policy

    def decide(self, request: DecisionRequest) -> DecisionResponse:
        features = build_features(request.entered)
        probability = self._scorer.probability_of_default(features)
        decision = decide(RuleInputs(default_probability=probability), self._policy)
        return DecisionResponse(
            outcome=decision.outcome,
            reasons=list(decision.reasons),
            features=asdict(features),
            default_probability=probability,
            model_version=self._scorer.model_version,
        )
