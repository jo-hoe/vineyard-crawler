"""Tests for waterway query builder and array construction."""
from __future__ import annotations

from typing import Any

import numpy as np
import pytest

from vineyard_crawler.bbox import GERMANY
from vineyard_crawler.waterway import WaterwayArrays, _arrays_from_payload, build_waterway_query


def test_build_waterway_query_contains_all_types() -> None:
    q = build_waterway_query(GERMANY, ["river", "stream"], timeout_s=120)
    assert '[out:json][timeout:120];' in q
    assert 'way["waterway"="river"]["name"]' in q
    assert 'way["waterway"="stream"]["name"]' in q
    assert q.rstrip().endswith("out geom qt;")


def test_build_waterway_query_rejects_empty_types() -> None:
    with pytest.raises(ValueError):
        build_waterway_query(GERMANY, [], timeout_s=120)


def test_build_waterway_query_rejects_non_positive_timeout() -> None:
    with pytest.raises(ValueError):
        build_waterway_query(GERMANY, ["river"], timeout_s=0)


def _payload(elements: list[dict[str, Any]]) -> dict[str, Any]:
    return {"elements": elements}


def _way(name: str, pts: list[tuple[float, float]]) -> dict[str, Any]:
    return {
        "type": "way",
        "id": 1,
        "tags": {"waterway": "river", "name": name},
        "geometry": [{"lat": lat, "lon": lon} for lat, lon in pts],
    }


def test_arrays_from_payload_flat_structure() -> None:
    payload = _payload([
        _way("Rhein", [(50.0, 8.0), (50.1, 8.1)]),
        _way("Mosel", [(49.5, 7.0)]),
    ])
    arrays = _arrays_from_payload(payload)
    assert arrays.size == 3
    assert list(arrays.names) == ["Rhein", "Rhein", "Mosel"]
    assert arrays.lats[0] == pytest.approx(50.0)
    assert arrays.cos_lats.shape == arrays.lats.shape


def test_arrays_from_empty_payload() -> None:
    arrays = _arrays_from_payload(_payload([]))
    assert arrays.size == 0
