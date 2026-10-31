"""Which concrete parts the decision service is built from."""

from typing import cast

from fastapi import Request
from sqlalchemy import create_engine

from credit_backend.clients.extraction import ExtractionClient
from credit_backend.clients.wording import WordingClient
from credit_backend.config import Settings
from credit_backend.decisions.records import DecisionRecords
from credit_backend.decisions.rules import Policy
from credit_backend.decisions.scoring import GasparBaselineScorer, RegisteredScorer, Scorer
from credit_backend.decisions.service import DecisionService


def build_baseline() -> Scorer:
    return GasparBaselineScorer()


def build_scorer(settings: Settings) -> Scorer:
    """The model that MODEL_A names, such as wandb-registry-model/model-a:production.

    Without MODEL_A, the baseline scores.
    """
    return (
        RegisteredScorer.from_registry(settings.model_a) if settings.model_a else build_baseline()
    )


def build_records(settings: Settings) -> DecisionRecords:
    return DecisionRecords(create_engine(settings.database_url))


def build_wording(settings: Settings) -> WordingClient | None:
    if settings.model_c is None:
        return None
    return WordingClient(settings.ollama_url, settings.model_c)


def build_service(settings: Settings) -> DecisionService:
    scorer = build_scorer(settings)
    records = build_records(settings)
    records.create_schema()
    return DecisionService(
        scorer=scorer,
        extraction=ExtractionClient(settings.extraction_url),
        wording=build_wording(settings),
        records=records,
        policy=Policy(
            threshold=scorer.threshold,
        ),
    )


def get_service(request: Request) -> DecisionService:
    return cast(DecisionService, request.app.state.service)
