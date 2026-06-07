"""CSV export for :class:`Vineyard` rows."""
from __future__ import annotations

import csv
from pathlib import Path
from typing import Iterable

from .vineyard import Vineyard

CSV_FIELDS: tuple[str, ...] = (
    "osm_type",
    "osm_id",
    "name",
    "latitude",
    "longitude",
    "area_ha",
    "grape_variety",
    "wikipedia",
    "wikidata",
    "operator",
    "website",
    "locality",
    "classification",
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
