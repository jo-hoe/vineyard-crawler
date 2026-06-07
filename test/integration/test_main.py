"""End-to-end smoke test: main.py with a stubbed Overpass response."""
from __future__ import annotations

import csv
from pathlib import Path
from typing import Any

import main as entrypoint


class _FakeResponse:
    def __init__(self, payload: Any) -> None:
        self._payload = payload
        self.status_code = 200

    def raise_for_status(self) -> None:
        return None

    def json(self) -> Any:
        return self._payload


_VINEYARD_PAYLOAD = {
    "elements": [
        {
            "type": "way",
            "id": 1,
            "tags": {"landuse": "vineyard", "name": "Goldberg"},
            "geometry": [
                {"lat": 49.70, "lon": 8.10},
                {"lat": 49.70, "lon": 8.11},
                {"lat": 49.71, "lon": 8.11},
                {"lat": 49.71, "lon": 8.10},
                {"lat": 49.70, "lon": 8.10},
            ],
        }
    ]
}

_WATERWAY_PAYLOAD = {
    "elements": [
        {
            "type": "way",
            "id": 99,
            "tags": {"waterway": "river", "name": "Rhein"},
            "geometry": [
                {"lat": 49.50, "lon": 8.10},
                {"lat": 49.60, "lon": 8.20},
            ],
        }
    ]
}


def test_main_writes_csv_with_river_enrichment(tmp_path: Path, mocker: Any) -> None:
    mocker.patch(
        "vineyard_crawler.overpass.requests.post",
        side_effect=[
            _FakeResponse(_VINEYARD_PAYLOAD),
            _FakeResponse(_WATERWAY_PAYLOAD),
        ],
    )
    out = tmp_path / "vineyards.csv"
    rc = entrypoint.main(["--output", str(out)])
    assert rc == 0
    with out.open(encoding="utf-8", newline="") as fh:
        rows = list(csv.DictReader(fh))
    assert len(rows) == 1
    assert rows[0]["name"] == "Goldberg"
    assert rows[0]["osm_type"] == "way"
    assert rows[0]["nearest_river"] == "Rhein"
    assert int(rows[0]["river_distance_m"]) > 0


def test_main_skips_enrichment_when_no_waterway(tmp_path: Path, mocker: Any) -> None:
    post = mocker.patch(
        "vineyard_crawler.overpass.requests.post",
        return_value=_FakeResponse(_VINEYARD_PAYLOAD),
    )
    out = tmp_path / "vineyards.csv"
    rc = entrypoint.main(["--output", str(out), "--waterway"])
    assert rc == 0
    assert post.call_count == 1  # only vineyard fetch, no waterway fetch
    with out.open(encoding="utf-8", newline="") as fh:
        rows = list(csv.DictReader(fh))
    assert rows[0]["nearest_river"] == ""
    assert rows[0]["river_distance_m"] == ""
