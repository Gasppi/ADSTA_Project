"""The one way this backend builds an HTTP client."""

import httpx


def build_client(base_url: str) -> httpx.Client:
    # Task 7e: give every call a timeout that fits the service it calls. Reading two documents
    # on a CPU takes far longer than httpx waits by default. Decide whether to retry.
    return httpx.Client(base_url=base_url)
