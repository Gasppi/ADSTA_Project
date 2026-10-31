"""One row for every decision, so that any decision can be explained later."""

from collections.abc import Mapping, Sequence
from datetime import UTC, datetime

from sqlalchemy import JSON, DateTime, Engine, select
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column

from credit_backend.contracts import DecisionRecordRead, Outcome, Reason


class Base(DeclarativeBase):
    pass


class DecisionRecord(Base):
    __tablename__ = "decision_record"

    id: Mapped[int] = mapped_column(primary_key=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
    # The features the model saw. A value nobody could read is NULL, never 0.
    age: Mapped[float | None]
    dependents: Mapped[float | None]
    rev_util: Mapped[float | None]
    late_90: Mapped[float | None]
    monthly_inc: Mapped[float | None]
    debt_ratio: Mapped[float | None]
    # The other inputs of the rules.
    has_loss_certificate: Mapped[bool | None]
    extraction_checkpoint: Mapped[str | None]
    # What the decision rests on and what it was.
    default_probability: Mapped[float | None]
    model_version: Mapped[str]
    outcome: Mapped[str]
    reasons: Mapped[list[str]] = mapped_column(JSON)
    wording: Mapped[str | None]


class DecisionRecords:
    def __init__(self, engine: Engine) -> None:
        self._engine = engine

    def create_schema(self) -> None:
        """Creates the table if it is missing. It never changes a table that exists."""
        Base.metadata.create_all(self._engine)

    def save(
        self,
        *,
        features: Mapping[str, float | None],
        has_loss_certificate: bool | None,
        extraction_checkpoint: str | None,
        default_probability: float | None,
        model_version: str,
        outcome: Outcome,
        reasons: Sequence[Reason],
        wording: str | None,
    ) -> int:
        """Writes one row for one decision and returns its id."""
        row = DecisionRecord(
            **features,
            has_loss_certificate=has_loss_certificate,
            extraction_checkpoint=extraction_checkpoint,
            default_probability=default_probability,
            model_version=model_version,
            outcome=outcome.value,
            reasons=[reason.value for reason in reasons],
            wording=wording,
        )
        with Session(self._engine) as session:
            session.add(row)
            session.commit()
            return row.id

    def recent(self, limit: int) -> list[DecisionRecordRead]:
        statement = select(DecisionRecord).order_by(DecisionRecord.id.desc()).limit(limit)
        with Session(self._engine) as session:
            return [DecisionRecordRead.model_validate(row) for row in session.scalars(statement)]
