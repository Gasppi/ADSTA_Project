"""One decision, from the confirmed application to the stored answer."""

from dataclasses import asdict

from credit_backend.clients.extraction import Extractor
from credit_backend.clients.wording import WordingWriter
from credit_backend.contracts import (
    DecisionRecordRead,
    DecisionRequest,
    DecisionResponse,
    ExtractionResult,
)
from credit_backend.decisions.features import build_features
from credit_backend.decisions.records import DecisionRecords
from credit_backend.decisions.rules import Policy, RuleInputs, decide
from credit_backend.decisions.scoring import Scorer


class DecisionService:
    def __init__(
        self,
        scorer: Scorer,
        extraction: Extractor,
        wording: WordingWriter | None,
        records: DecisionRecords,
        policy: Policy,
    ) -> None:
        self._scorer = scorer
        self._extraction = extraction
        self._wording = wording
        self._records = records
        self._policy = policy

    def extract(self, payslip: bytes, debt_register: bytes) -> ExtractionResult:
        """What the documents say, before a case worker has confirmed any of it."""
        return self._extraction.extract(payslip, debt_register)

    def decide(self, request: DecisionRequest) -> DecisionResponse:
        """Decides on the figures the case worker confirmed. It reads no document itself."""
        entered = request.entered
        features = build_features(entered)
        probability = self._scorer.probability_of_default(features)
        decision = decide(
            RuleInputs(
                default_probability=probability,
                monthly_income=entered.monthly_income,
                has_loss_certificate=entered.has_loss_certificate,
            ),
            self._policy,
        )
        wording = (
            None
            if self._wording is None
            else self._wording.word(decision.outcome, decision.reasons)
        )
        record_id = self._records.save(
            features=asdict(features),
            has_loss_certificate=entered.has_loss_certificate,
            extraction_checkpoint=request.extraction_checkpoint,
            default_probability=probability,
            model_version=self._scorer.model_version,
            outcome=decision.outcome,
            reasons=decision.reasons,
            wording=wording,
        )
        return DecisionResponse(
            outcome=decision.outcome,
            reasons=list(decision.reasons),
            wording=wording,
            features=asdict(features),
            default_probability=probability,
            model_version=self._scorer.model_version,
            record_id=record_id,
        )

    def recent(self, limit: int) -> list[DecisionRecordRead]:
        return self._records.recent(limit)

    def close(self) -> None:
        self._extraction.close()
        if self._wording is not None:
            self._wording.close()
