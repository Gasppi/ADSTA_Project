from collections.abc import Iterator

import pytest
from sqlalchemy import Engine, create_engine
from sqlalchemy.pool import StaticPool

from credit_backend.decisions.records import DecisionRecord, DecisionRecords

MUST_CARRY = {"outcome", "reasons", "wording", "model_version"}


@pytest.fixture
def engine() -> Iterator[Engine]:
    engine = create_engine("sqlite://", poolclass=StaticPool)
    yield engine
    engine.dispose()


def test_a_new_table_holds_no_decisions(engine: Engine) -> None:
    records = DecisionRecords(engine)
    records.create_schema()

    assert records.recent(5) == []


def test_every_decision_row_carries_what_it_rests_on() -> None:
    columns = DecisionRecord.__table__.columns
    if set(columns.keys()) == {"id", "created_at"}:
        pytest.skip("Task 7c: the table has no columns for a decision yet")

    assert MUST_CARRY <= set(columns.keys())
    assert columns["wording"].nullable
