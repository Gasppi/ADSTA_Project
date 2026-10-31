from __future__ import annotations

from collections.abc import Sequence
from typing import Final

from credit_extraction.documents.fields import read_documents
from credit_extraction.documents.reader import Answer
from sample_documents import ground_truth, payslip_in, register_in

GROUND_TRUTH: Final = ground_truth()
CHECKPOINT: Final = "stub-checkpoint"


class StubReader:
    checkpoint = CHECKPOINT

    def __init__(self, says: str = "") -> None:
        self._says = says

    def ask(self, pdf: bytes, questions: Sequence[str]) -> dict[str, Answer]:
        return {question: Answer(text=self._says, score=1.0) for question in questions}


def _documents(index: int) -> tuple[bytes, bytes]:
    return (
        payslip_in(index).read_bytes(),
        register_in(index).read_bytes(),
    )


def test_the_result_names_the_reader_that_answered() -> None:
    payslip, debt_register = _documents(0)

    read = read_documents(StubReader(), payslip, debt_register)

    assert read.checkpoint == CHECKPOINT


def test_a_name_on_both_documents_reports_one_applicant() -> None:
    entry = GROUND_TRUTH[0]
    payslip, debt_register = _documents(entry["index"])

    read = read_documents(StubReader(entry["employee"]), payslip, debt_register)

    assert read.debt_register.applicant_name == entry["employee"]
    assert read.same_applicant is True


def test_a_name_on_neither_document_is_reported_as_a_disagreement() -> None:
    payslip, debt_register = _documents(0)

    read = read_documents(StubReader("Ruedi Wüthrich"), payslip, debt_register)

    assert read.same_applicant is False


def test_a_name_nobody_could_read_is_neither_a_warning_nor_an_assurance() -> None:
    payslip, debt_register = _documents(0)

    read = read_documents(StubReader(), payslip, debt_register)

    assert read.debt_register.applicant_name is None
    assert read.same_applicant is None
