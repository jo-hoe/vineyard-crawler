"""Tests for the bounding-box value object."""
from __future__ import annotations

import pytest

from vineyard_crawler.bbox import GERMANY, BoundingBox


def test_germany_constant_matches_expected_extent() -> None:
    assert GERMANY.as_overpass() == "47.0,6.0,55.0,15.0"


def test_parse_round_trips() -> None:
    bbox = BoundingBox.parse("47,6,55,15")
    assert bbox == GERMANY


def test_parse_rejects_wrong_arity() -> None:
    with pytest.raises(ValueError):
        BoundingBox.parse("47,6,55")


def test_parse_rejects_non_numeric() -> None:
    with pytest.raises(ValueError):
        BoundingBox.parse("a,b,c,d")


@pytest.mark.parametrize(
    "south,west,north,east",
    [
        (55.0, 6.0, 47.0, 15.0),  # south >= north
        (47.0, 15.0, 55.0, 6.0),  # west >= east
        (-91.0, 6.0, 55.0, 15.0),  # south out of range
        (47.0, 6.0, 91.0, 15.0),  # north out of range
        (47.0, -181.0, 55.0, 15.0),  # west out of range
        (47.0, 6.0, 55.0, 181.0),  # east out of range
    ],
)
def test_invalid_bbox_rejected(
    south: float, west: float, north: float, east: float
) -> None:
    with pytest.raises(ValueError):
        BoundingBox(south=south, west=west, north=north, east=east)
