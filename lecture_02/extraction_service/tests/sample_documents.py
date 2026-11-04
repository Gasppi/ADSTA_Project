"""The forty sample applicants in data/sample-documents at the root of the repository."""

import json
from pathlib import Path
from typing import Any, Final


def _find_documents() -> Path:
    for folder in Path(__file__).resolve().parents:
        documents = folder / "data" / "sample-documents"
        if documents.is_dir():
            return documents
    raise FileNotFoundError(f"There is no data/sample-documents above {Path(__file__).parent}.")


DOCUMENTS: Final = _find_documents()


def ground_truth() -> list[dict[str, Any]]:
    """What each applicant's two documents say, as they were generated."""
    return json.loads((DOCUMENTS / "ground_truth.json").read_text(encoding="utf-8"))


def payslip_in(index: int) -> Path:
    return _only(f"payslip_{index:03d}_*.pdf")


def register_in(index: int) -> Path:
    return _only(f"register_{index:03d}_*.pdf")


def _only(pattern: str) -> Path:
    found = sorted(DOCUMENTS.glob(pattern))
    if len(found) != 1:
        raise FileNotFoundError(f"{len(found)} documents match {pattern} in {DOCUMENTS}")
    return found[0]
