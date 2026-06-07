"""Overpass API client.

Honours the Overpass usage policy: identifies itself with a descriptive
``User-Agent`` and uses ``out geom`` so geometry comes back in the same
response — no second-pass node lookups.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

import requests

from . import __version__
from .bbox import BoundingBox

DEFAULT_ENDPOINT: str = "https://overpass-api.de/api/interpreter"
DEFAULT_TIMEOUT_S: int = 180
DEFAULT_USER_AGENT: str = (
    f"vineyard-crawler/{__version__} "
    "(+https://github.com/; OSM Overpass client)"
)


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
    """Thin, typed wrapper over ``requests`` for the Overpass interpreter."""

    endpoint: str = DEFAULT_ENDPOINT
    timeout_s: int = DEFAULT_TIMEOUT_S
    user_agent: str = DEFAULT_USER_AGENT

    def fetch(self, bbox: BoundingBox) -> Mapping[str, Any]:
        """Submit the query and return the parsed JSON response."""
        query = build_query(bbox, self.timeout_s)
        # HTTP timeout is given a small grace period over the server-side
        # timeout so the server's own error response can still reach us.
        http_timeout = self.timeout_s + 30
        response = requests.post(
            self.endpoint,
            data={"data": query},
            headers={
                "User-Agent": self.user_agent,
                "Accept": "application/json",
            },
            timeout=http_timeout,
        )
        response.raise_for_status()
        payload = response.json()
        if not isinstance(payload, dict):
            raise ValueError("Overpass response was not a JSON object")
        return payload
