"""Model C puts a decision that is already made into words. It decides nothing.

A borrowed example from outside credit shows what a good input and a good output look like.
A public library tells a member that their card is blocked.

    input:   outcome "blocked", reasons ["items_overdue"]
    output:  {"text": "Your library card is blocked because some items you borrowed are overdue."}

The input carries the decision and its reasons, and nothing else. It has no name, no figure
and no date. The output says what was decided and why, and it adds nothing the input did not
carry.
"""

import json
import logging
from collections.abc import Sequence
from typing import Final, Protocol

import httpx
from ollama import Client, ResponseError
from pydantic import BaseModel, ConfigDict, ValidationError

from credit_backend.contracts import Outcome, Reason

logger = logging.getLogger(__name__)

# A Model C that hangs must not hang the decision. The first call is the slowest, because
# Ollama loads the model into memory then.
WORDING_TIMEOUT_SECONDS: Final = 60.0


class Worded(BaseModel):
    """The only shape of answer the backend accepts from Model C."""

    model_config = ConfigDict(extra="forbid")

    text: str


SYSTEM_PROMPT: Final = (
    "You write a short message to a loan applicant about a decision that has already been made. "
    "You receive the outcome and the reasons, and nothing else. "
    "Say what was decided and why, using only the reasons you receive. "
    "Write one or two plain sentences. "
    "Never change, question or soften the outcome. "
    "Never add names, figures, dates, advice or promises that are not in the input. "
    'Answer with JSON that has one field, "text".'
)

# temperature 0 takes the most probable token, and the seed fixes the rest, so the same
# decision gets the same wording. num_predict stops a long answer, num_ctx keeps the memory small.
OPTIONS: Final[dict[str, float | int]] = {
    "temperature": 0,
    "seed": 42,
    "num_predict": 120,
    "num_ctx": 2048,
}


def user_prompt(outcome: Outcome, reasons: Sequence[Reason]) -> str:
    """The outcome and the reasons, and nothing else, in the form of the library example."""
    names = json.dumps([reason.value for reason in reasons])
    return f'outcome "{outcome.value}", reasons {names}'


def validated(content: str | None) -> str | None:
    """The text Model C wrote, or None when it is not the shape the backend accepts."""
    if content is None:
        return None
    try:
        text = Worded.model_validate_json(content).text.strip()
    except ValidationError:
        logger.warning("Model C answered with something that is not the expected JSON")
        return None
    return text or None


class WordingWriter(Protocol):
    def word(self, outcome: Outcome, reasons: Sequence[Reason]) -> str | None: ...

    def close(self) -> None: ...


class WordingClient:
    def __init__(self, host: str, model: str, transport: httpx.BaseTransport | None = None) -> None:
        self._client = Client(host=host, transport=transport, timeout=WORDING_TIMEOUT_SECONDS)
        self.model = model

    def close(self) -> None:
        self._client.close()

    def word(self, outcome: Outcome, reasons: Sequence[Reason]) -> str | None:
        """The decision in words, or None when Model C gave nothing the backend can use."""
        try:
            response = self._client.chat(
                model=self.model,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt(outcome, reasons)},
                ],
                options=OPTIONS,
                format=Worded.model_json_schema(),
            )
        except (ConnectionError, httpx.TimeoutException, ResponseError) as error:
            # Ollama is down, too slow, or Model C is not pulled. The decision goes on.
            logger.warning("No wording from %s: %s: %s", self.model, type(error).__name__, error)
            return None
        return validated(response.message.content)
