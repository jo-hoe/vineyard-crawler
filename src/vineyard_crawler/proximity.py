"""Nearest-waterway proximity lookup using vectorised Haversine + bbox pre-filter."""
from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

from .geometry import EARTH_RADIUS_M, LatLon
from .waterway import WaterwayArrays

# Bounding-box margin in degrees used to pre-filter river vertices before the
# full Haversine scan.  0.5° ≈ 55 km — generous enough that no vineyard in
# Germany can have a nearer river point outside this window.
_BBOX_MARGIN_DEG: float = 0.5


@dataclass(frozen=True)
class ProximityResult:
    nearest_river: str
    river_distance_m: int


def _subarray(
    arrays: WaterwayArrays,
    boundary_points: tuple[LatLon, ...],
) -> WaterwayArrays:
    """Return a spatially filtered view of *arrays* around *boundary_points*.

    Falls back to the full arrays when no river vertex falls within the margin,
    which handles vineyards far from any named river.
    """
    lats = np.array([p.lat for p in boundary_points])
    lons = np.array([p.lon for p in boundary_points])
    mask = (
        (arrays.lats >= lats.min() - _BBOX_MARGIN_DEG)
        & (arrays.lats <= lats.max() + _BBOX_MARGIN_DEG)
        & (arrays.lons >= lons.min() - _BBOX_MARGIN_DEG)
        & (arrays.lons <= lons.max() + _BBOX_MARGIN_DEG)
    )
    if not mask.any():
        return arrays
    return WaterwayArrays(
        lats=arrays.lats[mask],
        lons=arrays.lons[mask],
        cos_lats=arrays.cos_lats[mask],
        names=arrays.names[mask],
    )


def _min_distance(
    boundary_points: tuple[LatLon, ...],
    sub: WaterwayArrays,
) -> tuple[float, str]:
    """Return (distance_m, river_name) for the closest river vertex to any
    boundary point, using vectorised Haversine over all boundary points at once.
    """
    pt_lats = np.radians(np.array([p.lat for p in boundary_points]))  # (P,)
    pt_lons = np.radians(np.array([p.lon for p in boundary_points]))  # (P,)
    cos_pt_lats = np.cos(pt_lats)                                      # (P,)

    # Broadcast: (P, 1) vs (1, N) → (P, N)
    dlat = pt_lats[:, None] - np.radians(sub.lats)[None, :]
    dlon = pt_lons[:, None] - np.radians(sub.lons)[None, :]
    a = (
        np.sin(dlat / 2) ** 2
        + cos_pt_lats[:, None] * sub.cos_lats[None, :] * np.sin(dlon / 2) ** 2
    )
    dists = 2.0 * EARTH_RADIUS_M * np.arcsin(np.sqrt(np.clip(a, 0.0, 1.0)))  # (P, N)

    flat_idx = int(np.argmin(dists))
    river_idx = flat_idx % sub.size
    return float(dists.flat[flat_idx]), str(sub.names[river_idx])


def nearest_waterway(
    boundary_points: tuple[LatLon, ...],
    arrays: WaterwayArrays,
) -> ProximityResult | None:
    """Return the name and distance (metres) of the nearest waterway vertex
    to any point on the vineyard boundary polygon.

    Returns ``None`` when *arrays* is empty or *boundary_points* is empty.
    """
    if arrays.size == 0 or not boundary_points:
        return None

    sub = _subarray(arrays, boundary_points)
    dist_m, name = _min_distance(boundary_points, sub)
    return ProximityResult(nearest_river=name, river_distance_m=round(dist_m))
