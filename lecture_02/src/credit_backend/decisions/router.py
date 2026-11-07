from typing import Annotated

from fastapi import APIRouter, Depends, File, UploadFile

from credit_backend.contracts import (
    DecisionRecordRead,
    DecisionRequest,
    DecisionResponse,
    ExtractionResult,
)
from credit_backend.decisions.dependencies import get_service
from credit_backend.decisions.service import DecisionService

router = APIRouter()


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.post("/extractions")
def create_extraction(
    service: Annotated[DecisionService, Depends(get_service)],
    payslip: Annotated[UploadFile, File()],
    debt_register: Annotated[UploadFile, File()],
) -> ExtractionResult:
    """Reads the two documents and decides nothing. A case worker confirms the figures first."""
    return service.extract(payslip.file.read(), debt_register.file.read())


@router.post("/decisions")
def create_decision(
    service: Annotated[DecisionService, Depends(get_service)], request: DecisionRequest
) -> DecisionResponse:
    return service.decide(request)


@router.get("/decisions/recent")
def recent_decisions(
    service: Annotated[DecisionService, Depends(get_service)], limit: int = 20
) -> list[DecisionRecordRead]:
    return service.recent(limit)
