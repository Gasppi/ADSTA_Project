"""The page's only way to talk to the backend.

Every call returns either the JSON the backend answered or a `Failure`. It never raises for a
backend that is down, slow or answers with an error, so the page can always show a sentence.
"""

from dataclasses import dataclass
from enum import StrEnum, auto
from typing import Any

import httpx

RECENT_LIMIT = 20


class FailureKind(StrEnum):
    NO_CONNECTION = auto()
    """The request never reached the backend: refused, unknown host, or no connection in time."""
    NO_ANSWER_IN_TIME = auto()
    """The request was sent, but no complete answer came back. The backend may still have
    acted on it, so a decision may have been recorded."""
    STATUS = auto()
    """The backend answered with a status other than 200."""
    INVALID_ANSWER = auto()
    """The backend answered 200, but not with JSON of the expected shape."""


@dataclass(frozen=True)
class Failure:
    kind: FailureKind
    status_code: int | None = None
    detail: Any = None
    """The `detail` of the error body, if the backend sent one."""


@dataclass(frozen=True)
class Upload:
    name: str
    content: bytes
    content_type: str | None

    def as_file(self) -> tuple[str, bytes, str | None]:
        """The form httpx expects for one file of a multipart body."""
        return (self.name, self.content, self.content_type)


type Answer[T] = T | Failure


def _detail(response: httpx.Response) -> Any:
    try:
        body = response.json()
    except ValueError:
        return None
    return body.get("detail") if isinstance(body, dict) else None


class BackendClient:
    def __init__(
        self,
        base_url: str,
        *,
        extraction_timeout_seconds: float,
        decision_timeout_seconds: float,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self._base_url = base_url
        self._extraction_timeout = httpx.Timeout(extraction_timeout_seconds)
        self._decision_timeout = httpx.Timeout(decision_timeout_seconds)
        self._transport = transport

    def _send(self, method: str, path: str, **kwargs: Any) -> Answer[Any]:
        try:
            with httpx.Client(base_url=self._base_url, transport=self._transport) as client:
                response = client.request(method, path, **kwargs)
        except (httpx.ConnectError, httpx.ConnectTimeout, httpx.PoolTimeout):
            # Nothing was sent: a stopped backend refuses the connection right away.
            return Failure(FailureKind.NO_CONNECTION)
        except httpx.TransportError:
            # The request went out, but the answer did not come back (in time). A paused or
            # slow backend ends here, and it may still store the decision.
            return Failure(FailureKind.NO_ANSWER_IN_TIME)
        if response.status_code != httpx.codes.OK:
            return Failure(FailureKind.STATUS, response.status_code, _detail(response))
        try:
            return response.json()
        except ValueError:
            return Failure(FailureKind.INVALID_ANSWER, response.status_code)

    def extract(self, payslip: Upload, debt_register: Upload) -> Answer[dict[str, Any]]:
        """POST /extractions. Reads the two documents and decides nothing."""
        files = {
            "payslip": payslip.as_file(),
            "debt_register": debt_register.as_file(),
        }
        answer = self._send("POST", "/extractions", files=files, timeout=self._extraction_timeout)
        if isinstance(answer, Failure) or _is_extraction(answer):
            return answer
        return Failure(FailureKind.INVALID_ANSWER, httpx.codes.OK)

    def decide(self, body: dict[str, Any]) -> Answer[dict[str, Any]]:
        """POST /decisions. Every call creates a new record."""
        answer = self._send("POST", "/decisions", json=body, timeout=self._decision_timeout)
        if isinstance(answer, Failure) or _is_decision(answer):
            return answer
        return Failure(FailureKind.INVALID_ANSWER, httpx.codes.OK)

    def recent(self, limit: int = RECENT_LIMIT) -> Answer[list[dict[str, Any]]]:
        """GET /decisions/recent, newest first. Uses httpx's default timeout."""
        answer = self._send("GET", "/decisions/recent", params={"limit": limit})
        if isinstance(answer, Failure):
            return answer
        if isinstance(answer, list) and all(isinstance(row, dict) for row in answer):
            return answer
        return Failure(FailureKind.INVALID_ANSWER, httpx.codes.OK)


def _is_extraction(answer: Any) -> bool:
    return (
        isinstance(answer, dict)
        and isinstance(answer.get("payslip"), dict)
        and isinstance(answer.get("debt_register"), dict)
        and isinstance(answer.get("checkpoint"), str)
    )


def _is_decision(answer: Any) -> bool:
    return (
        isinstance(answer, dict)
        and isinstance(answer.get("outcome"), str)
        and isinstance(answer.get("reasons"), list)
        and isinstance(answer.get("record_id"), int)
    )
