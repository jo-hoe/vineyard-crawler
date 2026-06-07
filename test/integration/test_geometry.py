"""Tests for spherical geometry helpers."""
from __future__ import annotations

import math

import pytest

from vineyard_crawler.geometry import (
    LatLon,
    centroid,
    polygon_area_ha,
    ring_area_m2,
)


def _square_ring(
    lat0: float, lon0: float, side_deg: float
) -> list[LatLon]:
    """Build a degenerate-but-fine 'square' in lat/lon for sanity checks."""
    return [
        LatLon(lat0, lon0),
        LatLon(lat0, lon0 + side_deg),
        LatLon(lat0 + side_deg, lon0 + side_deg),
        LatLon(lat0 + side_deg, lon0),
    ]


def test_ring_area_one_degree_square_near_equator_is_about_12365_km2() -> None:
    # A 1° lat × 1° lon square near the equator is well-known to be ~12,365 km^2.
    ring = _square_ring(0.0, 0.0, 1.0)
    area_m2 = ring_area_m2(ring)
    area_km2 = area_m2 / 1_000_000.0
    assert math.isclose(area_km2, 12_365.0, rel_tol=0.01)


def test_ring_area_handles_already_closed_ring() -> None:
    open_ring = _square_ring(48.0, 8.0, 0.001)
    closed_ring = open_ring + [open_ring[0]]
    assert math.isclose(
        ring_area_m2(open_ring), ring_area_m2(closed_ring), rel_tol=1e-12
    )


def test_ring_area_zero_for_degenerate_input() -> None:
    assert ring_area_m2([]) == 0.0
    assert ring_area_m2([LatLon(0, 0), LatLon(1, 1)]) == 0.0


def test_polygon_area_ha_sums_rings() -> None:
    r1 = _square_ring(48.0, 8.0, 0.01)
    r2 = _square_ring(48.5, 8.5, 0.01)
    expected_ha = (
        ring_area_m2(r1) + ring_area_m2(r2)
    ) / 10_000.0
    assert math.isclose(polygon_area_ha([r1, r2]), expected_ha, rel_tol=1e-12)


def test_centroid_is_arithmetic_mean() -> None:
    pts = [LatLon(0.0, 0.0), LatLon(2.0, 4.0), LatLon(4.0, 2.0)]
    c = centroid(pts)
    assert math.isclose(c.lat, 2.0)
    assert math.isclose(c.lon, 2.0)


def test_centroid_rejects_empty() -> None:
    with pytest.raises(ValueError):
        centroid([])
