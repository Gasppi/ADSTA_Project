"""Model B reads words and positions from the first PDF page. OCR is not supported."""

from __future__ import annotations

import io
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any, Final, Protocol, cast

import pdfplumber
from transformers import pipeline

NORMALISED_SCALE: Final[int] = 1000

# One answer, whose two values arrive behind an untyped mapping.
_Prediction = Mapping[str, Any]


class _QuestionAnswering(Protocol):
    """The one call this file makes on the pipeline."""

    device: object

    def __call__(
        self,
        *,
        image: None,
        question: str,
        word_boxes: Sequence[tuple[str, list[int]]],
    ) -> _Prediction | list[_Prediction]: ...


@dataclass(frozen=True)
class Answer:
    text: str
    score: float


class Reader(Protocol):
    """Everything the reading functions ask of Model B."""

    @property
    def checkpoint(self) -> str: ...

    def ask(self, pdf: bytes, questions: Sequence[str]) -> dict[str, Answer]: ...


@dataclass(frozen=True)
class _Page:
    words: list[str]
    boxes: list[list[int]]


class DocumentReader:
    def __init__(self, checkpoint: str, revision: str, device: str | None = None) -> None:
        self._pipeline = cast(
            _QuestionAnswering,
            pipeline(
                "document-question-answering",
                model=checkpoint,
                revision=revision,
                device=device,
            ),
        )
        self.checkpoint = f"{checkpoint}@{revision}"
        self.device = str(self._pipeline.device)

    def ask(self, pdf: bytes, questions: Sequence[str]) -> dict[str, Answer]:
        page = _first_page(pdf)
        return {question: self._ask_one(page, question) for question in questions}

    def _ask_one(self, page: _Page, question: str) -> Answer:
        result = self._pipeline(
            image=None,
            question=question,
            word_boxes=list(zip(page.words, page.boxes, strict=True)),
        )
        best = result[0] if isinstance(result, list) else result
        return Answer(text=str(best["answer"]), score=float(best["score"]))


def page_text(pdf: bytes) -> str:
    """The first page as printed text, for the questions a reader cannot answer."""
    with pdfplumber.open(io.BytesIO(pdf)) as document:
        return document.pages[0].extract_text() or ""


def _first_page(pdf: bytes) -> _Page:
    with pdfplumber.open(io.BytesIO(pdf)) as document:
        page = document.pages[0]
        width, height = page.width, page.height
        extracted = page.extract_words()

    words = [str(word["text"]) for word in extracted]
    boxes = [
        [
            int(word["x0"] / width * NORMALISED_SCALE),
            int(word["top"] / height * NORMALISED_SCALE),
            int(word["x1"] / width * NORMALISED_SCALE),
            int(word["bottom"] / height * NORMALISED_SCALE),
        ]
        for word in extracted
    ]
    return _Page(words=words, boxes=boxes)
