"""One row for every decision, so that any decision can be explained later."""

from datetime import UTC, datetime

from sqlalchemy import DateTime, Engine, select
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column

from credit_backend.contracts import DecisionRecordRead


class Base(DeclarativeBase):
    pass


class DecisionRecord(Base):
    __tablename__ = "decision_record"

    id: Mapped[int] = mapped_column(primary_key=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
    # Task 7c: a column for everything the decision rests on. That is at least the features,
    # the outcome, the reasons, the wording and the model version, in columns named outcome,
    # reasons, wording and model_version. A value nobody could read is stored as NULL, never as 0.


class DecisionRecords:
    def __init__(self, engine: Engine) -> None:
        self._engine = engine

    def create_schema(self) -> None:
        """Creates the table if it is missing. It never changes a table that exists."""
        Base.metadata.create_all(self._engine)

    def save(self) -> int:
        # Task 7c: take what the row stores, write one row, and return its id. Change the
        # parameters to what your service hands over.
        raise NotImplementedError("Task 7c: store one decision")

    def recent(self, limit: int) -> list[DecisionRecordRead]:
        statement = select(DecisionRecord).order_by(DecisionRecord.id.desc()).limit(limit)
        with Session(self._engine) as session:
            return [DecisionRecordRead.model_validate(row) for row in session.scalars(statement)]
