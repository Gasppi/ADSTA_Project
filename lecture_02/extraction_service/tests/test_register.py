from __future__ import annotations

import io
from collections.abc import Sequence
from datetime import date
from typing import Final

from credit_extraction.documents.fields import read_register, same_applicant
from credit_extraction.documents.reader import Answer
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen.canvas import Canvas
from sample_documents import ground_truth, payslip_in, register_in

GROUND_TRUTH: Final = ground_truth()


class StubReader:
    checkpoint = "stub-checkpoint"

    def __init__(self, says: str = "") -> None:
        self._says = says

    def ask(self, pdf: bytes, questions: Sequence[str]) -> dict[str, Answer]:
        return {question: Answer(text=self._says, score=1.0) for question in questions}


def _index_where(**wanted: object) -> int:
    return next(
        entry["index"]
        for entry in GROUND_TRUTH
        if all(entry[key] == value for key, value in wanted.items())
    )


def _read(index: int, says: str = "") -> bool | None:
    pdf = register_in(index).read_bytes()
    return read_register(StubReader(says), pdf).has_loss_certificate


def test_an_extract_recording_a_certificate_reports_one() -> None:
    assert _read(_index_where(has_loss_certificate=True)) is True


def test_an_extract_with_proceedings_and_no_certificate_reports_none_of_them() -> None:
    assert _read(_index_where(has_loss_certificate=False, proceedings_count=1)) is False


def test_an_empty_extract_reports_no_certificate() -> None:
    assert _read(_index_where(proceedings_count=0)) is False


def test_a_page_that_certifies_nothing_is_absent_rather_than_false() -> None:
    read = read_register(StubReader(), _a_readable_page_that_is_not_an_extract())

    assert read.has_loss_certificate is None
    assert read.date_of_birth is None


def test_a_page_with_no_text_layer_is_absent_rather_than_false() -> None:
    read = read_register(StubReader(), _a_page_with_no_text_layer())

    assert read.has_loss_certificate is None


def test_the_model_is_what_answers_when_it_answers() -> None:
    assert _read(_index_where(has_loss_certificate=True), says="keine") is False


def test_a_span_that_is_neither_a_count_nor_a_word_falls_back_to_the_page() -> None:
    assert _read(_index_where(has_loss_certificate=True), says="unverjährter") is True


def test_a_date_of_birth_is_read_from_the_span_the_model_returned() -> None:
    read = read_register(StubReader("14.06.1978"), _a_page_with_no_text_layer())

    assert read.date_of_birth == date(1978, 6, 14)


def test_a_birth_date_the_model_could_not_find_is_absent_rather_than_guessed() -> None:
    read = read_register(StubReader("CHF 17.00"), _a_page_with_no_text_layer())

    assert read.date_of_birth is None


def _a_readable_page_that_is_not_an_extract() -> bytes:
    buffer = io.BytesIO()
    canvas = Canvas(buffer, pagesize=A4)
    canvas.drawString(60, 700, "Ein Blatt Papier mit Text, aber ohne Bescheinigung.")
    canvas.showPage()
    canvas.save()
    return buffer.getvalue()


def _a_page_with_no_text_layer() -> bytes:
    buffer = io.BytesIO()
    canvas = Canvas(buffer, pagesize=A4)
    canvas.rect(50, 50, 200, 100)
    canvas.showPage()
    canvas.save()
    return buffer.getvalue()


def test_the_applicant_is_read_off_the_extract() -> None:
    read = read_register(StubReader("Schuldner: Anna Furrer,"), _a_page_with_no_text_layer())

    assert read.applicant_name == "Schuldner: Anna Furrer"


def test_two_documents_naming_one_person_raise_no_warning() -> None:
    name = str(GROUND_TRUTH[0]["employee"])
    payslip = payslip_in(int(str(GROUND_TRUTH[0]["index"]))).read_bytes()

    assert same_applicant(name, payslip) is True


def test_a_name_that_is_not_on_the_payslip_is_reported() -> None:
    other = str(GROUND_TRUTH[1]["employee"])
    payslip = payslip_in(int(str(GROUND_TRUTH[0]["index"]))).read_bytes()

    assert same_applicant(other, payslip) is False


def test_a_name_nobody_could_read_is_neither_a_warning_nor_an_assurance() -> None:
    payslip = payslip_in(int(str(GROUND_TRUTH[0]["index"]))).read_bytes()

    assert same_applicant(None, payslip) is None


def test_a_payslip_with_no_text_layer_cannot_confirm_the_applicant() -> None:
    assert same_applicant("Anna Furrer", _a_page_with_no_text_layer()) is False
