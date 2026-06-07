"""Vineyard model and Overpass-element parsing."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable, Mapping, Sequence

from .geometry import LatLon, centroid, polygon_area_ha


@dataclass(frozen=True)
class Vineyard:
    """A named vineyard site derived from one OSM way or relation."""

    osm_type: str
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


# --- Overpass element parsing ------------------------------------------------

_RELATION_OUTER_ROLES = frozenset({"outer", ""})


def _geometry_to_ring(geom: Sequence[Mapping[str, Any]]) -> list[LatLon]:
    return [LatLon(lat=float(p["lat"]), lon=float(p["lon"])) for p in geom]


def _way_rings(element: Mapping[str, Any]) -> list[list[LatLon]]:
    geom = element.get("geometry")
    if not geom:
        return []
    return [_geometry_to_ring(geom)]


def _relation_rings(element: Mapping[str, Any]) -> list[list[LatLon]]:
    rings: list[list[LatLon]] = []
    for member in element.get("members", ()):  # type: ignore[arg-type]
        if member.get("type") != "way":
            continue
        if member.get("role") not in _RELATION_OUTER_ROLES:
            continue
        geom = member.get("geometry")
        if not geom:
            continue
        rings.append(_geometry_to_ring(geom))
    return rings


def _rings_for(element: Mapping[str, Any]) -> list[list[LatLon]]:
    osm_type = element.get("type")
    if osm_type == "way":
        return _way_rings(element)
    if osm_type == "relation":
        return _relation_rings(element)
    return []


def _optional_tag(tags: Mapping[str, str], key: str) -> str | None:
    value = tags.get(key)
    if value is None:
        return None
    stripped = value.strip()
    return stripped or None


def from_overpass_element(element: Mapping[str, Any]) -> Vineyard | None:
    """Build a :class:`Vineyard` from one Overpass element.

    Returns ``None`` for elements that lack a name, lack usable geometry, or
    are of an unsupported OSM type — the caller filters these out.
    """
    osm_type = element.get("type")
    if osm_type not in ("way", "relation"):
        return None

    tags: Mapping[str, str] = element.get("tags") or {}
    name = _optional_tag(tags, "name")
    if name is None:
        return None

    rings = _rings_for(element)
    rings = [r for r in rings if len(r) >= 3]
    if not rings:
        return None

    all_points: list[LatLon] = [pt for ring in rings for pt in ring]
    c = centroid(all_points)
    area_ha = polygon_area_ha(rings)

    # Merge website + contact:website; prefer the bare key when both present.
    website = _optional_tag(tags, "website") or _optional_tag(tags, "contact:website")

    return Vineyard(
        osm_type=str(osm_type),
        osm_id=int(element["id"]),
        name=name,
        latitude=c.lat,
        longitude=c.lon,
        area_ha=area_ha,
        grape_variety=_optional_tag(tags, "grape_variety"),
        wikipedia=_optional_tag(tags, "wikipedia"),
        wikidata=_optional_tag(tags, "wikidata"),
        operator=_optional_tag(tags, "operator"),
        website=website,
        locality=_optional_tag(tags, "vineyard:locality"),
        classification=_optional_tag(tags, "vineyard:class"),
    )


def from_overpass_response(payload: Mapping[str, Any]) -> list[Vineyard]:
    """Parse the full Overpass JSON response into vineyards, dropping invalid ones."""
    elements: Iterable[Mapping[str, Any]] = payload.get("elements") or ()
    vineyards: list[Vineyard] = []
    for el in elements:
        v = from_overpass_element(el)
        if v is not None:
            vineyards.append(v)
    return vineyards
