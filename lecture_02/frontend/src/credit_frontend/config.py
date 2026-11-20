"""What the page reads from the environment when it starts.

None of the three values has a default. Docker Compose sets them. The two timeouts were
measured on 2026-11-20 (see docs/page_spec.md), and changing them needs no code change.
"""

import os
from collections.abc import Mapping
from dataclasses import dataclass


class ConfigError(RuntimeError):
    """A required environment variable is missing or does not fit."""


@dataclass(frozen=True)
class Settings:
    backend_url: str
    """Where the backend answers, read from BACKEND_URL."""

    extraction_timeout_seconds: float
    """How long the page waits for POST /extractions, read from EXTRACTION_TIMEOUT_SECONDS."""

    decision_timeout_seconds: float
    """How long the page waits for POST /decisions, read from DECISION_TIMEOUT_SECONDS."""


def _required(environ: Mapping[str, str], name: str) -> str:
    value = environ.get(name, "").strip()
    if not value:
        message = f"Set {name} in the environment. The page has no default for it."
        raise ConfigError(message)
    return value


def _seconds(environ: Mapping[str, str], name: str) -> float:
    raw = _required(environ, name)
    try:
        seconds = float(raw)
    except ValueError as error:
        message = f"{name} must be a number of seconds, not {raw!r}."
        raise ConfigError(message) from error
    if not seconds > 0:
        message = f"{name} must be above 0 seconds, not {raw!r}."
        raise ConfigError(message)
    return seconds


def load_settings(environ: Mapping[str, str] | None = None) -> Settings:
    environ = os.environ if environ is None else environ
    return Settings(
        backend_url=_required(environ, "BACKEND_URL"),
        extraction_timeout_seconds=_seconds(environ, "EXTRACTION_TIMEOUT_SECONDS"),
        decision_timeout_seconds=_seconds(environ, "DECISION_TIMEOUT_SECONDS"),
    )
