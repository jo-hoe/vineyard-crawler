"""Overpass fetch for waterway elements.

Returns flat numpy arrays covering all polyline vertices for the requested
waterway types, with a parallel name array so proximity lookup can report
the nearest river name without a second scan.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Sequence

import numpy as np

from .bbox import BoundingBox
from .overpass import OverpassClient

DEFAULT_WATERWAY_TYPES: tuple[str, ...] = ("river",)


def build_waterway_query(
    bbox: BoundingBox,
    waterway_types: Sequence[str],
    timeout_s: int,
) -> str:
    if not waterway_types:
        raise ValueError("waterway_types must not be empty")
    if timeout_s <= 0:
        raise ValueError(f"timeout_s must be positive, got {timeout_s}")
    box = bbox.as_overpass()
    statements = "\n".join(
        f'  way["waterway"="{wt}"]["name"]({box});' for wt in waterway_types
    )
    return (
        f"[out:json][timeout:{timeout_s}];\n"
        "(\n"
        f"{statements}\n"
        ");\n"
        "out geom qt;\n"
    )


@dataclass(frozen=True)
class WaterwayArrays:
    """Flat numpy arrays of all waterway vertices, ready for vectorised lookup."""

    lats: np.ndarray      # shape (N,)  float64
    lons: np.ndarray      # shape (N,)  float64
    cos_lats: np.ndarray  # shape (N,)  precomputed cos(radians(lat))
    names: np.ndarray     # shape (N,)  object (str)

    @property
    def size(self) -> int:
        return int(self.lats.size)


def _arrays_from_payload(payload: Mapping[str, Any]) -> WaterwayArrays:
    all_lats: list[float] = []
    all_lons: list[float] = []
    all_names: list[str] = []

    for el in payload.get("elements") or ():
        name: str = (el.get("tags") or {}).get("name") or ""
        for pt in el.get("geometry") or ():
            all_lats.append(float(pt["lat"]))
            all_lons.append(float(pt["lon"]))
            all_names.append(name)

    lats = np.array(all_lats, dtype=np.float64)
    lons = np.array(all_lons, dtype=np.float64)
    return WaterwayArrays(
        lats=lats,
        lons=lons,
        cos_lats=np.cos(np.radians(lats)),
        names=np.array(all_names, dtype=object),
    )


def fetch_waterways(
    client: OverpassClient,
    bbox: BoundingBox,
    waterway_types: Sequence[str] = DEFAULT_WATERWAY_TYPES,
) -> WaterwayArrays:
    """Fetch waterway geometries from Overpass and return flat vertex arrays."""
    query = build_waterway_query(bbox, waterway_types, client.timeout_s)
    payload = client.post_query(query)
    return _arrays_from_payload(payload)
