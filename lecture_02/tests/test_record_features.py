from dataclasses import asdict

from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool

from credit_backend.contracts import SAMPLE_REQUEST, DecisionRequest, Outcome
from credit_backend.decisions.features import build_features
from credit_backend.decisions.records import DecisionRecord, DecisionRecords

ENTERED = DecisionRequest.model_validate(SAMPLE_REQUEST).entered


def test_every_feature_has_a_column() -> None:
    features = asdict(build_features(ENTERED))

    assert set(features) <= set(DecisionRecord.__table__.columns.keys())


def test_a_real_feature_vector_is_stored_and_read_back() -> None:
    records = DecisionRecords(create_engine("sqlite://", poolclass=StaticPool))
    records.create_schema()
    features = asdict(build_features(ENTERED))

    record_id = records.save(
        features=features,
        has_loss_certificate=ENTERED.has_loss_certificate,
        extraction_checkpoint=None,
        default_probability=0.1,
        model_version="test",
        outcome=Outcome.APPROVED,
        reasons=[],
        wording=None,
    )

    stored = records.recent(1)[0]
    assert stored.id == record_id
    assert stored.monthly_inc == features["monthly_inc"]
    assert stored.debt_ratio == features["debt_ratio"]
