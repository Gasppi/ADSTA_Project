"""The one way this backend builds an HTTP client."""

from typing import Final

import httpx

# Reading two documents on a CPU is slow, so the extraction service gets a long read timeout.
# The other limits stay short, so that a service that is down is noticed within seconds.
# There is no retry: a second try would double the wait, and the case worker can send the
# documents again.
EXTRACTION_TIMEOUT: Final = httpx.Timeout(connect=5.0, read=180.0, write=30.0, pool=5.0)


def build_client(base_url: str, timeout: httpx.Timeout = EXTRACTION_TIMEOUT) -> httpx.Client:
    return httpx.Client(base_url=base_url, timeout=timeout)
