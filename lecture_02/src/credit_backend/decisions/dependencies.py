"""Which concrete parts the decision service is built from."""

from typing import cast

from fastapi import Request

from credit_backend.decisions.rules import Policy
from credit_backend.decisions.scoring import PlaceholderScorer
from credit_backend.decisions.service import DecisionService


def build_service() -> DecisionService:
    # Task 6: replace the placeholder with the baseline your team chose.
    scorer = PlaceholderScorer()
    return DecisionService(
        scorer=scorer,
        policy=Policy(
            threshold=scorer.threshold,
        ),
    )


def get_service(request: Request) -> DecisionService:
    return cast(DecisionService, request.app.state.service)
