"""Tests for the Overpass query builder and HTTP client."""
from __future__ import annotations

from typing import Any

import pytest

from vineyard_crawler.bbox import GERMANY
from vineyard_crawler.overpass import (
    DEFAULT_ENDPOINT,
    OverpassClient,
    build_query,
)


def test_query_includes_bbox_and_filters() -> None:
    q = build_query(GERMANY, timeout_s=180)
    assert "[out:json][timeout:180];" in q
    assert 'way["landuse"="vineyard"]["name"](47.0,6.0,55.0,15.0);' in q
    assert 'relation["landuse"="vineyard"]["name"](47.0,6.0,55.0,15.0);' in q
    assert q.rstrip().endswith("out geom;")


def test_query_rejects_non_positive_timeout() -> None:
    with pytest.raises(ValueError):
        build_query(GERMANY, timeout_s=0)


class _FakeResponse:
    def __init__(self, payload: Any, status: int = 200) -> None:
        self._payload = payload
        self.status_code = status

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")

    def json(self) -> Any:
        return self._payload


def test_fetch_posts_query_with_user_agent(mocker: Any) -> None:
    payload = {"elements": []}
    post = mocker.patch(
        "vineyard_crawler.overpass.requests.post",
        return_value=_FakeResponse(payload),
    )
    client = OverpassClient()
    result = client.fetch(GERMANY)
    assert result == payload
    args, kwargs = post.call_args
    assert args == (DEFAULT_ENDPOINT,)
    assert "data" in kwargs["data"]
    assert "vineyard-crawler/" in kwargs["headers"]["User-Agent"]
    assert kwargs["headers"]["Accept"] == "application/json"
    # HTTP timeout should exceed the server-side timeout
    assert kwargs["timeout"] > client.timeout_s


def test_fetch_rejects_non_object_payload(mocker: Any) -> None:
    mocker.patch(
        "vineyard_crawler.overpass.requests.post",
        return_value=_FakeResponse(["not", "an", "object"]),
    )
    with pytest.raises(ValueError):
        OverpassClient().fetch(GERMANY)
