"""Tests for parsing Overpass elements into Vineyard rows."""
from __future__ import annotations

from typing import Any

from vineyard_crawler.vineyard import (
    from_overpass_element,
    from_overpass_response,
)


def _way_element(
    osm_id: int = 1,
    name: str | None = "Goldberg",
    grape: str | None = None,
    extra_tags: dict[str, str] | None = None,
) -> dict[str, Any]:
    tags: dict[str, str] = {"landuse": "vineyard"}
    if name is not None:
        tags["name"] = name
    if grape is not None:
        tags["grape_variety"] = grape
    if extra_tags:
        tags.update(extra_tags)
    return {
        "type": "way",
        "id": osm_id,
        "tags": tags,
        "geometry": [
            {"lat": 49.700, "lon": 8.100},
            {"lat": 49.700, "lon": 8.101},
            {"lat": 49.701, "lon": 8.101},
            {"lat": 49.701, "lon": 8.100},
            {"lat": 49.700, "lon": 8.100},
        ],
    }


def _relation_element(osm_id: int = 100) -> dict[str, Any]:
    return {
        "type": "relation",
        "id": osm_id,
        "tags": {"landuse": "vineyard", "name": "Großlage"},
        "members": [
            {
                "type": "way",
                "ref": 1,
                "role": "outer",
                "geometry": [
                    {"lat": 49.70, "lon": 8.10},
                    {"lat": 49.70, "lon": 8.11},
                    {"lat": 49.71, "lon": 8.11},
                    {"lat": 49.71, "lon": 8.10},
                    {"lat": 49.70, "lon": 8.10},
                ],
            },
            {
                "type": "way",
                "ref": 2,
                "role": "outer",
                "geometry": [
                    {"lat": 49.80, "lon": 8.20},
                    {"lat": 49.80, "lon": 8.21},
                    {"lat": 49.81, "lon": 8.21},
                    {"lat": 49.81, "lon": 8.20},
                    {"lat": 49.80, "lon": 8.20},
                ],
            },
            # Inner ring should be ignored by the outer-only filter.
            {
                "type": "way",
                "ref": 3,
                "role": "inner",
                "geometry": [
                    {"lat": 49.705, "lon": 8.105},
                    {"lat": 49.705, "lon": 8.106},
                    {"lat": 49.706, "lon": 8.106},
                ],
            },
        ],
    }


def test_way_parsed_with_centroid_and_area() -> None:
    v = from_overpass_element(_way_element(grape="Riesling"))
    assert v is not None
    assert v.osm_type == "way"
    assert v.osm_id == 1
    assert v.name == "Goldberg"
    assert v.grape_variety == "Riesling"
    assert v.wikipedia is None
    assert v.wikidata is None
    # centroid should sit roughly inside the small square
    assert 49.700 <= v.latitude <= 49.701
    assert 8.100 <= v.longitude <= 8.101
    assert v.area_ha > 0


def test_relation_aggregates_outer_ways_and_skips_inner() -> None:
    v = from_overpass_element(_relation_element())
    assert v is not None
    assert v.osm_type == "relation"
    # Two outer rings far apart → centroid lat falls between them
    assert 49.70 < v.latitude < 49.81
    # Area is the sum of both outer rings
    assert v.area_ha > 0


def test_unnamed_element_dropped() -> None:
    assert from_overpass_element(_way_element(name=None)) is None


def test_unsupported_type_dropped() -> None:
    node = {
        "type": "node",
        "id": 5,
        "tags": {"landuse": "vineyard", "name": "Punkt"},
    }
    assert from_overpass_element(node) is None


def test_optional_tags_round_trip() -> None:
    v = from_overpass_element(
        _way_element(
            extra_tags={
                "wikipedia": "de:Goldberg (Wein)",
                "wikidata": "Q12345",
            }
        )
    )
    assert v is not None
    assert v.wikipedia == "de:Goldberg (Wein)"
    assert v.wikidata == "Q12345"


def test_blank_tag_is_treated_as_missing() -> None:
    v = from_overpass_element(_way_element(extra_tags={"wikidata": "  "}))
    assert v is not None
    assert v.wikidata is None


def test_response_parser_filters_invalid_elements() -> None:
    payload = {
        "elements": [
            _way_element(osm_id=1),
            _way_element(osm_id=2, name=None),  # dropped: no name
            _relation_element(osm_id=100),
            {"type": "node", "id": 5, "tags": {"name": "x"}},  # dropped
        ]
    }
    result = from_overpass_response(payload)
    assert [v.osm_id for v in result] == [1, 100]
