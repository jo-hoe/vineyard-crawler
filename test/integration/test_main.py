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


def test_main_writes_csv(tmp_path: Path, mocker: Any) -> None:
    payload = {
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
    mocker.patch(
        "vineyard_crawler.overpass.requests.post",
        return_value=_FakeResponse(payload),
    )

    out = tmp_path / "vineyards.csv"
    rc = entrypoint.main(["--output", str(out)])
    assert rc == 0
    with out.open(encoding="utf-8", newline="") as fh:
        rows = list(csv.DictReader(fh))
    assert len(rows) == 1
    assert rows[0]["name"] == "Goldberg"
    assert rows[0]["osm_type"] == "way"
