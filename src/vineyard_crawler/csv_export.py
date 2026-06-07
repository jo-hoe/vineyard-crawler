"""CSV export for :class:`Vineyard` rows."""
from __future__ import annotations

import csv
import dataclasses
from pathlib import Path
from typing import Iterable

from .vineyard import Vineyard

# Field order for the output CSV.  Derived from the dataclass but excludes
# internal-only fields that have no meaning outside the process.
_EXCLUDED_FIELDS: frozenset[str] = frozenset({"boundary_points"})

CSV_FIELDS: tuple[str, ...] = tuple(
    f.name
    for f in dataclasses.fields(Vineyard)
    if f.name not in _EXCLUDED_FIELDS
)


def _row(v: Vineyard) -> dict[str, str]:
    return {
        "osm_type": v.osm_type,
        "osm_id": str(v.osm_id),
        "name": v.name,
        "latitude": f"{v.latitude:.7f}",
        "longitude": f"{v.longitude:.7f}",
        "area_ha": f"{v.area_ha:.4f}",
        "grape_variety": v.grape_variety or "",
        "wikipedia": v.wikipedia or "",
        "wikidata": v.wikidata or "",
        "operator": v.operator or "",
        "website": v.website or "",
        "locality": v.locality or "",
        "classification": v.classification or "",
        "nearest_river": v.nearest_river or "",
        "river_distance_m": str(v.river_distance_m) if v.river_distance_m is not None else "",
    }


def write_csv(vineyards: Iterable[Vineyard], path: Path) -> int:
    """Write *vineyards* to *path*; return the number of rows written."""
    path.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(CSV_FIELDS))
        writer.writeheader()
        for v in vineyards:
            writer.writerow(_row(v))
            count += 1
    return count
