"""The backend's side of the Information Extraction Service."""

from typing import Protocol

import httpx

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
        try:
            response = self._client.post(
                "/extractions", files={"payslip": payslip, "debt_register": debt_register}
            )
            response.raise_for_status()
            return ExtractionResult.model_validate(response.json())
        except (httpx.HTTPError, ValueError) as error:
            # HTTPError covers no answer, too late and an error status. ValueError covers an
            # answer that is not the expected JSON.
            message = f"The Information Extraction Service gave no result: {error!r}"
            raise ExtractionUnavailableError(message) from error
