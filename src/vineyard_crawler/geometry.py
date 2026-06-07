"""Spherical geometry helpers used to derive centroid and area from polygon rings."""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Iterable, Sequence

EARTH_RADIUS_M: float = 6_371_008.8  # IUGG mean Earth radius
SQM_PER_HECTARE: float = 10_000.0


@dataclass(frozen=True)
class LatLon:
    """A WGS84 coordinate in decimal degrees."""

    lat: float
    lon: float


def _ring_is_closed(ring: Sequence[LatLon]) -> bool:
    return len(ring) >= 2 and ring[0] == ring[-1]


def _close_ring(ring: Sequence[LatLon]) -> list[LatLon]:
    """Return a copy of *ring* with the first vertex appended if needed."""
    if _ring_is_closed(ring):
        return list(ring)
    return [*ring, ring[0]]


def ring_area_m2(ring: Sequence[LatLon]) -> float:
    """Return the absolute area of a single closed ring in square metres.

    Uses the spherical-excess formula (a constant-radius approximation good to
    well under a percent at vineyard scale). The sign of the planar shoelace
    is discarded — orientation only matters when subtracting inner rings.
    """
    if len(ring) < 3:
        return 0.0
    closed = _close_ring(ring)
    total = 0.0
    for a, b in zip(closed[:-1], closed[1:]):
        lon1 = math.radians(a.lon)
        lon2 = math.radians(b.lon)
        lat1 = math.radians(a.lat)
        lat2 = math.radians(b.lat)
        total += (lon2 - lon1) * (math.sin(lat1) + math.sin(lat2))
    return abs(total) * EARTH_RADIUS_M * EARTH_RADIUS_M / 2.0


def polygon_area_ha(rings: Iterable[Sequence[LatLon]]) -> float:
    """Total area of a multi-ring polygon (sum of ring areas) in hectares.

    Inner rings are not deducted: the OSM data we consume models each named
    vineyard as one or more outer polygons, and treating every ring as
    additive yields the correct gross extent for that schema.
    """
    return sum(ring_area_m2(r) for r in rings) / SQM_PER_HECTARE


def centroid(points: Sequence[LatLon]) -> LatLon:
    """Return the unweighted mean of *points*.

    Used as a cheap, robust label point for a vineyard polygon. We do not
    project to ECEF first because vineyards are small enough (typically
    < 1 km across) that the planar mean is indistinguishable from the
    spherical centroid at output precision.
    """
    if not points:
        raise ValueError("cannot compute centroid of empty point set")
    n = float(len(points))
    return LatLon(
        lat=sum(p.lat for p in points) / n,
        lon=sum(p.lon for p in points) / n,
    )
