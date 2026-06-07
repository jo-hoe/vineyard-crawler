"""Tests for CSV export."""
from __future__ import annotations

import csv
from pathlib import Path

from vineyard_crawler.csv_export import CSV_FIELDS, write_csv
from vineyard_crawler.vineyard import Vineyard


def _sample(name: str = "Goldberg") -> Vineyard:
    return Vineyard(
        osm_type="way",
        osm_id=42,
        name=name,
        latitude=49.70054,
        longitude=8.10054,
        area_ha=1.2345,
        grape_variety="Riesling",
        wikipedia=None,
        wikidata="Q12345",
        operator="Weingut Müller",
        website="https://example.com",
        locality="Große Lage",
        classification="VDP.GROSSE LAGE",
        nearest_river="Rhein",
        river_distance_m=1234,
    )


def test_write_csv_round_trip(tmp_path: Path) -> None:
    out = tmp_path / "vineyards.csv"
    n = write_csv([_sample(), _sample("Roter Hang")], out)
    assert n == 2
    with out.open(encoding="utf-8", newline="") as fh:
        reader = csv.DictReader(fh)
        assert tuple(reader.fieldnames or ()) == CSV_FIELDS
        rows = list(reader)
    assert [r["name"] for r in rows] == ["Goldberg", "Roter Hang"]
    assert rows[0]["wikipedia"] == ""  # None → empty
    assert rows[0]["wikidata"] == "Q12345"
    assert rows[0]["operator"] == "Weingut Müller"
    assert rows[0]["website"] == "https://example.com"
    assert rows[0]["locality"] == "Große Lage"
    assert rows[0]["classification"] == "VDP.GROSSE LAGE"
    assert rows[0]["nearest_river"] == "Rhein"
    assert rows[0]["river_distance_m"] == "1234"
    assert rows[0]["latitude"].startswith("49.")


def test_write_csv_creates_parent_directories(tmp_path: Path) -> None:
    out = tmp_path / "deep" / "nested" / "vineyards.csv"
    write_csv([_sample()], out)
    assert out.exists()


def test_write_csv_empty_input_emits_header_only(tmp_path: Path) -> None:
    out = tmp_path / "empty.csv"
    n = write_csv([], out)
    assert n == 0
    text = out.read_text(encoding="utf-8")
    assert text.strip() == ",".join(CSV_FIELDS)


def test_unenriched_vineyard_emits_empty_river_columns(tmp_path: Path) -> None:
    v = Vineyard(
        osm_type="way", osm_id=1, name="Test",
        latitude=49.0, longitude=8.0, area_ha=1.0,
        grape_variety=None, wikipedia=None, wikidata=None,
        operator=None, website=None, locality=None, classification=None,
    )
    out = tmp_path / "unenriched.csv"
    write_csv([v], out)
    with out.open(encoding="utf-8", newline="") as fh:
        rows = list(csv.DictReader(fh))
    assert rows[0]["nearest_river"] == ""
    assert rows[0]["river_distance_m"] == ""
