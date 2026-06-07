"""Bounding-box value object."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class BoundingBox:
    """A geographic bounding box in decimal degrees (WGS84).

    Attributes are ordered to match the Overpass `(south,west,north,east)`
    convention so the box can be serialised directly into a query.
    """

    south: float
    west: float
    north: float
    east: float

    def __post_init__(self) -> None:
        if not -90.0 <= self.south <= 90.0:
            raise ValueError(f"south out of range: {self.south}")
        if not -90.0 <= self.north <= 90.0:
            raise ValueError(f"north out of range: {self.north}")
        if not -180.0 <= self.west <= 180.0:
            raise ValueError(f"west out of range: {self.west}")
        if not -180.0 <= self.east <= 180.0:
            raise ValueError(f"east out of range: {self.east}")
        if self.south >= self.north:
            raise ValueError("south must be < north")
        if self.west >= self.east:
            raise ValueError("west must be < east")

    def as_overpass(self) -> str:
        """Render as an Overpass `(south,west,north,east)` clause body."""
        return f"{self.south},{self.west},{self.north},{self.east}"

    @classmethod
    def parse(cls, text: str) -> "BoundingBox":
        """Parse a `south,west,north,east` string."""
        parts = [p.strip() for p in text.split(",")]
        if len(parts) != 4:
            raise ValueError(
                f"bbox must have 4 comma-separated values, got: {text!r}"
            )
        try:
            south, west, north, east = (float(p) for p in parts)
        except ValueError as exc:
            raise ValueError(f"bbox values must be numeric: {text!r}") from exc
        return cls(south=south, west=west, north=north, east=east)


GERMANY: BoundingBox = BoundingBox(south=47.0, west=6.0, north=55.0, east=15.0)
