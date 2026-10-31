from __future__ import annotations

from typing import Annotated, cast

from fastapi import APIRouter, Depends, File, Request, UploadFile

from credit_extraction.contracts import ExtractionResult
from credit_extraction.documents.fields import read_documents
from credit_extraction.documents.reader import DocumentReader

router = APIRouter()


def get_reader(request: Request) -> DocumentReader:
    """Read from application state, not from dependency_overrides."""
    return cast(DocumentReader, request.app.state.reader)


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.post("/extractions")
def extract(
    reader: Annotated[DocumentReader, Depends(get_reader)],
    payslip: Annotated[UploadFile, File()],
    debt_register: Annotated[UploadFile, File()],
) -> ExtractionResult:
    return read_documents(reader, payslip.file.read(), debt_register.file.read())
