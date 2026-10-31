"""Extract typed document fields, with a text fallback for loss certificates."""

from __future__ import annotations

import re
from collections.abc import Callable, Mapping, Sequence
from typing import Final

from credit_extraction.contracts import ExtractionResult, PayslipFields, RegisterExtractFields
from credit_extraction.documents.normalisation import (
    birth_date,
    certificate_count,
    monthly_salary,
    person_name,
)
from credit_extraction.documents.reader import Answer, Reader, page_text

CERTIFICATE_QUESTIONS: Final[tuple[str, ...]] = (
    # The time window prevents the model returning "20 Jahre" as the count.
    "Wie viele unverjährte und noch nicht getilgte Verlustscheine aus Pfändungen "
    "der letzten 20 Jahre sind verzeichnet?",
)
NAME_QUESTIONS: Final[tuple[str, ...]] = (
    "Name des Schuldners?",
    "Debtor name?",
    "Schuldner?",
    "Wie heisst der Schuldner?",
    "Auf wen lautet dieser Auszug?",
)

BIRTH_QUESTIONS: Final[tuple[str, ...]] = (
    "geb.?",
    "Geburtsdatum?",
)

PAYSLIP_QUESTIONS: Final[dict[str, tuple[str, ...]]] = {
    "gross": ("Wie hoch ist der Bruttolohn total?", "What is the gross salary?"),
}
NO_CERTIFICATES: Final = re.compile(r"(?:Es sind|Es ist)\s+keine\s+unverj")
SOME_CERTIFICATES: Final = re.compile(r"(?:Es sind|Es ist)\s+\d+\s+unverj")


def read_documents(reader: Reader, payslip: bytes, debt_register: bytes) -> ExtractionResult:
    """Both documents, read and held against each other."""
    register = read_register(reader, debt_register)
    return ExtractionResult(
        payslip=read_payslip(reader, payslip),
        debt_register=register,
        same_applicant=same_applicant(register.applicant_name, payslip),
        checkpoint=reader.checkpoint,
    )


def read_payslip(reader: Reader, pdf: bytes) -> PayslipFields:
    answers = _answers(reader, pdf, PAYSLIP_QUESTIONS)
    return PayslipFields(gross=monthly_salary(answers["gross"]))


def read_register(reader: Reader, pdf: bytes) -> RegisterExtractFields:
    """Read the name, birth date and certificate. Fall back to text for the certificate."""
    asked = reader.ask(pdf, [*CERTIFICATE_QUESTIONS, *BIRTH_QUESTIONS, *NAME_QUESTIONS])
    certificate = _first(asked, CERTIFICATE_QUESTIONS, certificate_count)
    return RegisterExtractFields(
        has_loss_certificate=(
            _loss_certificate(page_text(pdf)) if certificate is None else certificate
        ),
        date_of_birth=_first(asked, BIRTH_QUESTIONS, birth_date),
        applicant_name=person_name(_surest(asked, NAME_QUESTIONS)),
    )


def same_applicant(name: str | None, payslip: bytes) -> bool | None:
    """Whether the person the extract names is printed on the payslip."""
    if name is None:
        return None
    printed = " ".join(page_text(payslip).split()).casefold()
    return bool(printed) and name.casefold() in printed


def _surest(asked: Mapping[str, Answer], questions: Sequence[str]) -> str:
    """The answer the model was surest of, across every wording of one question."""
    return max((asked[one] for one in questions), key=lambda answer: answer.score).text


def _first[T](
    asked: Mapping[str, Answer], questions: Sequence[str], parse: Callable[[str], T | None]
) -> T | None:
    """Keep the first parseable answer. Confidence can favour the wrong clause."""
    for question in questions:
        read = parse(asked[question].text)
        if read is not None:
            return read
    return None


def _loss_certificate(printed: str) -> bool | None:
    """None when neither sentence is on the page, which is not the same as no."""
    flattened = " ".join(printed.split())
    if NO_CERTIFICATES.search(flattened):
        return False
    return True if SOME_CERTIFICATES.search(flattened) else None


def _answers(
    reader: Reader, pdf: bytes, questions: Mapping[str, tuple[str, ...]]
) -> dict[str, str]:
    """Asks every wording of every field at once, and keeps the surest answer."""
    asked = reader.ask(pdf, [one for wordings in questions.values() for one in wordings])
    return {
        name: max((asked[one] for one in wordings), key=lambda answer: answer.score).text
        for name, wordings in questions.items()
    }
