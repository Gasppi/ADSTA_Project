"""Which concrete parts the decision service is built from."""

import os
from typing import cast

from fastapi import Request

from credit_backend.decisions.rules import Policy
from credit_backend.decisions.scoring import GasparBaselineScorer, RegisteredScorer, Scorer
from credit_backend.decisions.scoring import GasparBaselineScorer
from credit_backend.decisions.service import DecisionService


def build_baseline() -> Scorer:
    # Task 1: return the baseline your team chose in lecture 2.
    return PlaceholderScorer()


def build_scorer() -> Scorer:
    """The model that MODEL_A names, such as wandb-registry-model/model-a:production.

    Without MODEL_A, the baseline scores.
    """
    path = os.environ.get("MODEL_A")
    return RegisteredScorer.from_registry(path) if path else build_baseline()


def build_service() -> DecisionService:
    scorer = build_scorer()
    # Task 6: replace the placeholder with the baseline your team chose.
    scorer = GasparBaselineScorer()
    return DecisionService(
        scorer=scorer,
        policy=Policy(
            threshold=scorer.threshold,
        ),
    )


def get_service(request: Request) -> DecisionService:
    return cast(DecisionService, request.app.state.service)
