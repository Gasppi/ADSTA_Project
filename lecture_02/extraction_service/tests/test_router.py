from __future__ import annotations

import io
from collections.abc import Sequence
from typing import Final

from credit_extraction.documents.reader import Answer
from credit_extraction.documents.router import get_reader, router
from fastapi import FastAPI
from fastapi.testclient import TestClient
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen.canvas import Canvas
from sample_documents import ground_truth, payslip_in, register_in

CHECKPOINT: Final = "stub-checkpoint"
GROUND_TRUTH: Final = ground_truth()
WITH_CERTIFICATE: Final = next(one["index"] for one in GROUND_TRUTH if one["has_loss_certificate"])


class StubReader:
    def __init__(self, answers: dict[str, str]) -> None:
        self._answers = answers
        self.checkpoint = CHECKPOINT

    def ask(self, pdf: bytes, questions: Sequence[str]) -> dict[str, Answer]:
        return {
            question: Answer(text=self._answers.get(question, ""), score=1.0)
            for question in questions
        }


def client(answers: dict[str, str]) -> TestClient:
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_reader] = lambda: StubReader(answers)
    return TestClient(app)


def test_the_service_reports_healthy() -> None:
    assert client({}).get("/health").json() == {"status": "ok"}


def test_both_documents_are_read_into_one_result() -> None:
    answers = {"Wie hoch ist der Bruttolohn total?": "CHF 6'000.00"}
    files = {
        "payslip": payslip_in(WITH_CERTIFICATE).read_bytes(),
        "debt_register": register_in(WITH_CERTIFICATE).read_bytes(),
    }

    body = client(answers).post("/extractions", files=files).json()

    assert body["payslip"]["gross"]["amount"] == "6000.00"
    assert body["payslip"]["gross"]["period"] == "monthly"
    assert body["debt_register"]["has_loss_certificate"] is True


def test_the_reply_names_the_checkpoint_that_read_the_documents() -> None:
    files = {
        "payslip": payslip_in(0).read_bytes(),
        "debt_register": register_in(0).read_bytes(),
    }

    body = client({}).post("/extractions", files=files).json()

    assert body["checkpoint"] == CHECKPOINT


def test_a_salary_the_reader_could_not_find_is_absent_rather_than_zero() -> None:
    files = {
        "payslip": payslip_in(0).read_bytes(),
        "debt_register": register_in(0).read_bytes(),
    }

    body = client({}).post("/extractions", files=files).json()

    assert body["payslip"]["gross"] is None


def test_a_register_the_service_could_not_read_does_not_arrive_as_a_clean_one() -> None:
    files = {
        "payslip": payslip_in(0).read_bytes(),
        "debt_register": _a_page_saying_nothing_of_the_kind(),
    }

    body = client({}).post("/extractions", files=files).json()

    assert body["debt_register"]["has_loss_certificate"] is None


def _a_page_saying_nothing_of_the_kind() -> bytes:
    buffer = io.BytesIO()
    canvas = Canvas(buffer, pagesize=A4)
    canvas.drawString(60, 700, "Dieses Blatt ist kein Auszug aus dem Betreibungsregister.")
    canvas.showPage()
    canvas.save()
    return buffer.getvalue()
