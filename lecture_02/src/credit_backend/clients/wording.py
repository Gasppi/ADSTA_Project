"""Model C puts a decision that is already made into words. It decides nothing.

A borrowed example from outside credit shows what a good input and a good output look like.
A public library tells a member that their card is blocked.

    input:   outcome "blocked", reasons ["items_overdue"]
    output:  {"text": "Your library card is blocked because some items you borrowed are overdue."}

The input carries the decision and its reasons, and nothing else. It has no name, no figure
and no date. The output says what was decided and why, and it adds nothing the input did not
carry.
"""

from collections.abc import Sequence
from typing import Final, Protocol

import httpx
from ollama import Client
from pydantic import BaseModel, ConfigDict

from credit_backend.contracts import Outcome, Reason


class Worded(BaseModel):
    """The only shape of answer the backend accepts from Model C."""

    model_config = ConfigDict(extra="forbid")

    text: str


# Task 6: the system prompt. It tells Model C what it does and what it must never do.
SYSTEM_PROMPT: Final = ""

# Task 6: the options that make the wording repeatable and short, such as temperature, seed
# and num_predict. Look each one up in the Ollama documentation before you set it.
OPTIONS: Final[dict[str, float | int]] = {}


def user_prompt(outcome: Outcome, reasons: Sequence[Reason]) -> str:
    # Task 6: build the user prompt from the outcome and the reasons, and from nothing else.
    raise NotImplementedError("Task 6: build the user prompt from the reasons")


def validated(content: str | None) -> str | None:
    # Task 6: validate what Model C answered with Worded, and return its text. Return None
    # when it does not validate.
    raise NotImplementedError("Task 6: validate what Model C answered")


class WordingWriter(Protocol):
    def word(self, outcome: Outcome, reasons: Sequence[Reason]) -> str | None: ...

    def close(self) -> None: ...


class WordingClient:
    def __init__(self, host: str, model: str, transport: httpx.BaseTransport | None = None) -> None:
        # Task 7e: give Ollama a timeout, so that a Model C that hangs cannot hang the decision.
        self._client = Client(host=host, transport=transport)
        self.model = model

    def close(self) -> None:
        self._client.close()

    def word(self, outcome: Outcome, reasons: Sequence[Reason]) -> str | None:
        """The decision in words, or None when Model C gave nothing the backend can use."""
        # Task 7e: return None when Ollama does not answer in time, so that the decision goes on.
        # The ollama package raises ConnectionError when Ollama is down, httpx.TimeoutException
        # when it is too slow, and ollama.ResponseError when Model C is not pulled. Log a warning
        # that names the cause, so that a missing wording is never a mystery.
        response = self._client.chat(
            model=self.model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt(outcome, reasons)},
            ],
            options=OPTIONS,
            format=Worded.model_json_schema(),
        )
        return validated(response.message.content)
