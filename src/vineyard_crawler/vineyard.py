"""Vineyard model and Overpass-element parsing."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterable, Literal, Mapping, Sequence

from .geometry import LatLon, centroid, polygon_area_ha

OsmType = Literal["way", "relation"]


@dataclass(frozen=True)
class Vineyard:
    """A named vineyard site derived from one OSM way or relation."""

    osm_type: OsmType
    osm_id: int
    name: str
    latitude: float
    longitude: float
    area_ha: float
    grape_variety: str | None
    wikipedia: str | None
    wikidata: str | None
    operator: str | None
    website: str | None
    locality: str | None
    classification: str | None
    # Boundary vertices — used for proximity lookup, not written to CSV.
    boundary_points: tuple[LatLon, ...] = field(default=(), compare=False, hash=False)
    # Populated after proximity enrichment; None means not yet computed.
    nearest_river: str | None = None
    river_distance_m: int | None = None


# ---------------------------------------------------------------------------
# Overpass element parsing
# ---------------------------------------------------------------------------

_RELATION_OUTER_ROLES: frozenset[str] = frozenset({"outer", ""})


def _geometry_to_ring(geom: Sequence[Mapping[str, Any]]) -> list[LatLon]:
    return [LatLon(lat=float(p["lat"]), lon=float(p["lon"])) for p in geom]


def _way_rings(element: Mapping[str, Any]) -> list[list[LatLon]]:
    geom = element.get("geometry")
    if not geom:
        return []
    return [_geometry_to_ring(geom)]


def _relation_rings(element: Mapping[str, Any]) -> list[list[LatLon]]:
    rings: list[list[LatLon]] = []
    for member in element.get("members") or ():
        if member.get("type") != "way":
            continue
        if member.get("role") not in _RELATION_OUTER_ROLES:
            continue
        geom = member.get("geometry")
        if geom:
            rings.append(_geometry_to_ring(geom))
    return rings


def _rings_for(osm_type: OsmType, element: Mapping[str, Any]) -> list[list[LatLon]]:
    if osm_type == "way":
        return _way_rings(element)
    return _relation_rings(element)


def _optional_tag(tags: Mapping[str, str], key: str) -> str | None:
    value = tags.get(key)
    if not value:
        return None
    return value.strip() or None


def _parse_tags(tags: Mapping[str, str]) -> dict[str, str | None]:
    website = _optional_tag(tags, "website") or _optional_tag(tags, "contact:website")
    return {
        "grape_variety": _optional_tag(tags, "grape_variety"),
        "wikipedia": _optional_tag(tags, "wikipedia"),
        "wikidata": _optional_tag(tags, "wikidata"),
        "operator": _optional_tag(tags, "operator"),
        "website": website,
        "locality": _optional_tag(tags, "vineyard:locality"),
        "classification": _optional_tag(tags, "vineyard:class"),
    }


def from_overpass_element(element: Mapping[str, Any]) -> Vineyard | None:
    """Build a :class:`Vineyard` from one Overpass element.

    Returns ``None`` for elements without a name, without usable geometry,
    or of an unsupported OSM type.
    """
    osm_type = element.get("type")
    if osm_type not in ("way", "relation"):
        return None
    typed: OsmType = osm_type  # type: ignore[assignment]

    tags: Mapping[str, str] = element.get("tags") or {}
    name = _optional_tag(tags, "name")
    if name is None:
        return None

    rings = [r for r in _rings_for(typed, element) if len(r) >= 3]
    if not rings:
        return None

    all_points = [pt for ring in rings for pt in ring]
    c = centroid(all_points)

    return Vineyard(
        osm_type=typed,
        osm_id=int(element["id"]),
        name=name,
        latitude=c.lat,
        longitude=c.lon,
        area_ha=polygon_area_ha(rings),
        boundary_points=tuple(all_points),
        **_parse_tags(tags),  # type: ignore[arg-type]
    )


def from_overpass_response(payload: Mapping[str, Any]) -> list[Vineyard]:
    """Parse the full Overpass JSON response into vineyards, dropping invalid ones."""
    elements: Iterable[Mapping[str, Any]] = payload.get("elements") or ()
    return [v for el in elements if (v := from_overpass_element(el)) is not None]
