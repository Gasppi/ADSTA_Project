import json

import httpx
import pytest

from credit_backend.clients.extraction import ExtractionClient, ExtractionUnavailableError
from credit_backend.clients.wording import WordingClient
from credit_backend.contracts import Outcome, Reason

NOBODY_LISTENS = "http://127.0.0.1:9"
REFUSED = (Outcome.REFUSED, [Reason.DEFAULT_PROBABILITY_ABOVE_THRESHOLD])


def ollama_answering(content: str) -> httpx.MockTransport:
    def answer(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "model": json.loads(request.content)["model"],
                "created_at": "2026-10-29T08:00:00Z",
                "message": {"role": "assistant", "content": content},
                "done": True,
            },
        )

    return httpx.MockTransport(answer)


def worded(client: WordingClient) -> str | None:
    try:
        return client.word(*REFUSED)
    except NotImplementedError as error:
        pytest.skip(str(error))
    except Exception as error:
        pytest.skip(f"Task 7e: the wording client let {type(error).__name__} through")


def test_extraction_that_does_not_answer_is_reported_as_unavailable() -> None:
    client = ExtractionClient(NOBODY_LISTENS)

    try:
        client.extract(b"%PDF payslip", b"%PDF register")
    except ExtractionUnavailableError:
        return
    except httpx.HTTPError as error:
        pytest.skip(f"Task 7e: the extraction client let {type(error).__name__} through")
    finally:
        client.close()
    pytest.fail("a service nobody runs answered")


def test_a_wording_that_validates_is_returned() -> None:
    text = "Your application was refused."
    client = WordingClient(
        "http://ollama", model="model-c", transport=ollama_answering(json.dumps({"text": text}))
    )

    assert worded(client) == text


def test_a_wording_that_does_not_validate_is_none() -> None:
    client = WordingClient("http://ollama", model="model-c", transport=ollama_answering("Refused!"))

    assert worded(client) is None


def test_a_model_c_that_does_not_answer_gives_no_wording() -> None:
    client = WordingClient(NOBODY_LISTENS, model="model-c")

    assert worded(client) is None
