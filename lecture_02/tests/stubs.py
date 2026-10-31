"""Stand-ins for Model A, the two services and the database, so that no test needs them."""

from collections.abc import Sequence
from typing import Final

from credit_backend.clients.extraction import ExtractionUnavailableError
from credit_backend.contracts import (
    DecisionRecordRead,
    ExtractionResult,
    Outcome,
    PayslipFields,
    Reason,
    RegisterExtractFields,
)
from credit_backend.decisions.rules import Policy
from credit_backend.decisions.scoring import PlaceholderScorer
from credit_backend.decisions.service import DecisionService

READ: Final = ExtractionResult(
    payslip=PayslipFields.model_validate(
        {"gross": {"amount": "6000.00", "currency": "CHF", "period": "monthly"}}
    ),
    debt_register=RegisterExtractFields(has_loss_certificate=False, applicant_name="Anna Furrer"),
    checkpoint="model-b@0123abc",
)


class StubExtraction:
    def __init__(self, result: ExtractionResult | None = READ) -> None:
        self._result = result

    def extract(self, payslip: bytes, debt_register: bytes) -> ExtractionResult:
        if self._result is None:
            raise ExtractionUnavailableError("stubbed as unreachable")
        return self._result

    def close(self) -> None:
        pass


class StubWording:
    def __init__(self, text: str | None = "Worded.") -> None:
        self._text = text
        self.asked: list[tuple[Outcome, tuple[Reason, ...]]] = []

    def word(self, outcome: Outcome, reasons: Sequence[Reason]) -> str | None:
        self.asked.append((outcome, tuple(reasons)))
        return self._text

    def close(self) -> None:
        pass


class StubRecords:
    """Takes whatever the service hands over, and answers with the id of a new row."""

    def __init__(self) -> None:
        self.saved: list[tuple[tuple[object, ...], dict[str, object]]] = []

    def create_schema(self) -> None:
        pass

    def save(self, *args: object, **kwargs: object) -> int:
        self.saved.append((args, kwargs))
        return len(self.saved)

    def recent(self, limit: int) -> list[DecisionRecordRead]:
        return []


def stub_service(
    extraction: StubExtraction | None = None,
    wording: StubWording | None = None,
    records: StubRecords | None = None,
) -> DecisionService:
    scorer = PlaceholderScorer()
    return DecisionService(
        scorer=scorer,
        extraction=extraction or StubExtraction(),
        wording=wording,
        records=records or StubRecords(),  # ty: ignore[invalid-argument-type]
        policy=Policy(threshold=scorer.threshold),
    )
