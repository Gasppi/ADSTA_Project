"""The backend's side of the Information Extraction Service."""

from typing import Protocol

from credit_backend.clients.http import build_client
from credit_backend.contracts import ExtractionResult


class ExtractionUnavailableError(RuntimeError):
    """The Information Extraction Service did not answer with a result."""


class Extractor(Protocol):
    def extract(self, payslip: bytes, debt_register: bytes) -> ExtractionResult: ...

    def close(self) -> None: ...


class ExtractionClient:
    def __init__(self, base_url: str) -> None:
        self._client = build_client(base_url)

    def close(self) -> None:
        self._client.close()

    def extract(self, payslip: bytes, debt_register: bytes) -> ExtractionResult:
        # Task 7e: when the service does not answer, answers too late or answers with an error,
        # raise ExtractionUnavailableError, so that main.py can answer with a clear 503.
        response = self._client.post(
            "/extractions", files={"payslip": payslip, "debt_register": debt_register}
        )
        return ExtractionResult.model_validate(response.json())
