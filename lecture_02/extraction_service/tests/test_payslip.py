from __future__ import annotations

import io
from collections.abc import Sequence
from typing import Final

from credit_extraction.documents.fields import read_payslip
from credit_extraction.documents.reader import Answer
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen.canvas import Canvas
from sample_documents import ground_truth, payslip_in

GROUND_TRUTH: Final = ground_truth()


class SilentReader:
    checkpoint = "stub-checkpoint"

    def ask(self, pdf: bytes, questions: Sequence[str]) -> dict[str, Answer]:
        return {question: Answer(text="", score=0.0) for question in questions}


def _page_with_no_text_layer() -> bytes:
    buffer = io.BytesIO()
    canvas = Canvas(buffer, pagesize=A4)
    canvas.rect(50, 50, 200, 100)
    canvas.showPage()
    canvas.save()
    return buffer.getvalue()


def test_an_income_the_reader_could_not_answer_comes_back_absent() -> None:
    pdf = payslip_in(GROUND_TRUTH[0]["index"]).read_bytes()

    fields = read_payslip(SilentReader(), pdf)

    assert fields.gross is None


def test_a_payslip_with_no_text_layer_reports_nothing_rather_than_a_figure() -> None:
    fields = read_payslip(SilentReader(), _page_with_no_text_layer())

    assert fields.gross is None
