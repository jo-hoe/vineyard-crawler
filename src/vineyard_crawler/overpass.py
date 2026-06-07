"""Overpass API client.

Honours the Overpass API usage policy:
  https://dev.overpass-api.de/overpass-doc/en/preface/commons.html
  https://wiki.openstreetmap.org/wiki/Overpass_API

Policy rules implemented here:
  - Descriptive User-Agent (policy: identify your client)
  - At most MAX_CONCURRENT_REQUESTS simultaneous requests per IP (policy: 2 slots)
  - Exponential-backoff retry on HTTP 429 (slot queue full) and 504 (server overload)
  - Single `out geom` query — no second-pass node lookups (minimises request count)
  - Soft daily limits: ≤ 10,000 requests/day, ≤ 1 GB/day (enforced by caller design)
"""
from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Mapping

import requests

from . import __version__
from .bbox import BoundingBox

log = logging.getLogger(__name__)

DEFAULT_ENDPOINT: str = "https://overpass-api.de/api/interpreter"
DEFAULT_TIMEOUT_S: int = 180
DEFAULT_USER_AGENT: str = (
    f"vineyard-crawler/{__version__} "
    "(+https://github.com/jo-hoe/vineyard-crawler; OSM Overpass client)"
)

# The public overpass-api.de instance grants 2 concurrent query slots per IP.
# https://dev.overpass-api.de/overpass-doc/en/preface/commons.html
MAX_CONCURRENT_REQUESTS: int = 2

# Retry policy for 429 (slot queue full) and 504 (server overload).
# Base delay doubles on each attempt: 5 s, 10 s, 20 s.
_RETRY_BASE_S: float = 5.0
_RETRY_MAX_ATTEMPTS: int = 3
_RETRYABLE_STATUS_CODES: frozenset[int] = frozenset({429, 504})

_HTTP_GRACE_S: int = 30

# Module-level semaphore shared across all OverpassClient instances in a
# process so parallel fetches from main.py cannot exceed the slot limit.
_concurrency_lock: threading.Semaphore = threading.Semaphore(MAX_CONCURRENT_REQUESTS)


def build_query(bbox: BoundingBox, timeout_s: int) -> str:
    """Render the Overpass QL query for named vineyards inside *bbox*."""
    if timeout_s <= 0:
        raise ValueError(f"timeout_s must be positive, got {timeout_s}")
    box = bbox.as_overpass()
    return (
        f"[out:json][timeout:{timeout_s}];\n"
        "(\n"
        f'  way["landuse"="vineyard"]["name"]({box});\n'
        f'  relation["landuse"="vineyard"]["name"]({box});\n'
        ");\n"
        "out geom;\n"
    )


@dataclass(frozen=True)
class OverpassClient:
    """Typed wrapper over ``requests`` for the Overpass interpreter.

    Thread-safe: multiple instances (or threads) share the module-level
    semaphore so the process never exceeds MAX_CONCURRENT_REQUESTS in flight.
    """

    endpoint: str = DEFAULT_ENDPOINT
    timeout_s: int = DEFAULT_TIMEOUT_S
    user_agent: str = DEFAULT_USER_AGENT

    def post_query(self, query: str) -> Mapping[str, Any]:
        """POST *query* to Overpass, retrying on 429/504 with exponential backoff.

        Acquires the shared concurrency semaphore before each attempt and
        releases it immediately after the response arrives, so other threads
        can proceed without waiting for caller-side processing.

        Raises :class:`requests.HTTPError` when all retries are exhausted.
        Raises :class:`ValueError` when the response body is not a JSON object.
        """
        delay = _RETRY_BASE_S
        for attempt in range(1, _RETRY_MAX_ATTEMPTS + 1):
            with _concurrency_lock:
                response = requests.post(
                    self.endpoint,
                    data={"data": query},
                    headers={
                        "User-Agent": self.user_agent,
                        "Accept": "application/json",
                    },
                    timeout=self.timeout_s + _HTTP_GRACE_S,
                )

            if response.status_code not in _RETRYABLE_STATUS_CODES:
                break

            if attempt == _RETRY_MAX_ATTEMPTS:
                # Final attempt — let raise_for_status surface the error.
                break

            log.warning(
                "Overpass returned HTTP %d (attempt %d/%d); retrying in %.0f s",
                response.status_code,
                attempt,
                _RETRY_MAX_ATTEMPTS,
                delay,
            )
            time.sleep(delay)
            delay *= 2.0

        response.raise_for_status()
        payload = response.json()
        if not isinstance(payload, dict):
            raise ValueError("Overpass response was not a JSON object")
        return payload

    def fetch(self, bbox: BoundingBox) -> Mapping[str, Any]:
        """Fetch named vineyards for *bbox* and return the raw JSON payload."""
        return self.post_query(build_query(bbox, self.timeout_s))
