"""Tests for nearest-waterway proximity lookup."""
from __future__ import annotations

import math

import numpy as np
import pytest

from vineyard_crawler.geometry import LatLon
from vineyard_crawler.proximity import ProximityResult, nearest_waterway
from vineyard_crawler.waterway import WaterwayArrays


def _arrays(pts: list[tuple[float, float, str]]) -> WaterwayArrays:
    lats = np.array([p[0] for p in pts], dtype=np.float64)
    lons = np.array([p[1] for p in pts], dtype=np.float64)
    return WaterwayArrays(
        lats=lats,
        lons=lons,
        cos_lats=np.cos(np.radians(lats)),
        names=np.array([p[2] for p in pts], dtype=object),
    )


def _boundary(*pts: tuple[float, float]) -> tuple[LatLon, ...]:
    return tuple(LatLon(lat, lon) for lat, lon in pts)


def test_returns_none_for_empty_arrays() -> None:
    arrays = _arrays([])
    result = nearest_waterway(_boundary((49.0, 7.0)), arrays)
    assert result is None


def test_returns_none_for_empty_boundary() -> None:
    arrays = _arrays([(49.0, 7.0, "Rhein")])
    result = nearest_waterway((), arrays)
    assert result is None


def test_nearest_point_on_boundary_is_used() -> None:
    # Vineyard boundary: two vertices — one far from the river, one very close.
    river_pt = (50.000, 8.000)
    far_pt   = (49.000, 7.000)   # ~160 km away
    near_pt  = (50.001, 8.001)   # ~130 m away

    arrays = _arrays([(*river_pt, "Rhein")])
    result = nearest_waterway(_boundary(far_pt, near_pt), arrays)

    assert result is not None
    assert result.nearest_river == "Rhein"
    # Should be close to the near_pt→river_pt distance, not far_pt's distance.
    assert result.river_distance_m < 200


def test_correct_river_name_returned() -> None:
    arrays = _arrays([
        (50.0, 8.0, "Rhein"),
        (48.0, 10.0, "Isar"),   # far away
    ])
    result = nearest_waterway(_boundary((50.001, 8.001)), arrays)
    assert result is not None
    assert result.nearest_river == "Rhein"


def test_distance_is_rounded_integer_metres() -> None:
    arrays = _arrays([(50.0, 8.0, "Rhein")])
    result = nearest_waterway(_boundary((50.001, 8.001)), arrays)
    assert result is not None
    assert isinstance(result.river_distance_m, int)
    assert result.river_distance_m > 0


def test_falls_back_to_full_scan_when_no_point_in_bbox() -> None:
    # River point is > 0.5° away — should still be found via full-scan fallback.
    arrays = _arrays([(50.0, 8.0, "DistantRiver")])
    result = nearest_waterway(_boundary((49.4, 7.4)), arrays)  # ~80 km away
    assert result is not None
    assert result.nearest_river == "DistantRiver"
