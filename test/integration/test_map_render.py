"""Tests for the interactive map renderer."""
from __future__ import annotations

import csv
from pathlib import Path

import pytest

from vineyard_crawler.map_render import (
    BUCKET_COLORS,
    DEFAULT_THRESHOLDS_M,
    SLIDER_MAX_M,
    _bucket_index,
    _bucket_labels,
    _project_to_web_mercator,
    render,
)


def test_bucket_index_for_distances() -> None:
    t = (10, 100, 500, 1000)
    assert _bucket_index(0, t) == 0
    assert _bucket_index(9, t) == 0
    assert _bucket_index(10, t) == 1     # boundary is exclusive
    assert _bucket_index(99, t) == 1
    assert _bucket_index(100, t) == 2
    assert _bucket_index(999, t) == 3
    assert _bucket_index(1000, t) == 4
    assert _bucket_index(50_000, t) == 4
    assert _bucket_index(None, t) == 4   # unenriched lands in last bucket


def test_default_thresholds_match_palette_size() -> None:
    # five buckets ↔ four boundaries
    assert len(BUCKET_COLORS) == len(DEFAULT_THRESHOLDS_M) + 1


def test_slider_max_exceeds_largest_default_threshold() -> None:
    assert SLIDER_MAX_M > max(DEFAULT_THRESHOLDS_M)


def test_web_mercator_round_trip_is_sane() -> None:
    # Equator+prime meridian → origin
    x, y = _project_to_web_mercator(0.0, 0.0)
    assert abs(x) < 1e-6 and abs(y) < 1e-6
    # Berlin should be in the positive quadrant
    x, y = _project_to_web_mercator(52.52, 13.405)
    assert x > 0 and y > 0


def _write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    fields = [
        "osm_type", "osm_id", "name", "latitude", "longitude", "area_ha",
        "grape_variety", "wikipedia", "wikidata", "operator", "website",
        "locality", "classification", "nearest_river", "river_distance_m",
    ]
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields)
        writer.writeheader()
        for r in rows:
            writer.writerow({**{f: "" for f in fields}, **r})


def test_render_emits_self_contained_html(tmp_path: Path) -> None:
    csv_path = tmp_path / "vineyards.csv"
    _write_csv(csv_path, [
        {"name": "Goldberg", "latitude": "49.7", "longitude": "8.1",
         "nearest_river": "Rhein", "river_distance_m": "120"},
        {"name": "Roter Hang", "latitude": "49.85", "longitude": "8.30",
         "nearest_river": "Rhein", "river_distance_m": "5500"},
    ])
    html_path = tmp_path / "map.html"
    n = render(csv_path, html_path)
    assert n == 2
    assert html_path.exists()
    text = html_path.read_text(encoding="utf-8")
    assert "<html" in text.lower()
    assert "Goldberg" in text
    assert "Rhein" in text
    # Bokeh embeds its JS inline so no <script src=> hops out to the network
    assert "bokeh" in text.lower()


def test_bucket_labels_match_thresholds() -> None:
    labels = _bucket_labels((100, 200, 300, 500))
    assert labels == [
        "< 100 m",
        "100–200 m",
        "200–300 m",
        "300–500 m",
        "≥ 500 m",
    ]


def test_bucket_labels_count_matches_palette() -> None:
    labels = _bucket_labels(DEFAULT_THRESHOLDS_M)
    assert len(labels) == len(BUCKET_COLORS)


def test_render_includes_visibility_checkboxes(tmp_path: Path) -> None:
    csv_path = tmp_path / "vineyards.csv"
    _write_csv(csv_path, [
        {"name": "X", "latitude": "49.7", "longitude": "8.1",
         "nearest_river": "Rhein", "river_distance_m": "120"},
    ])
    html_path = tmp_path / "map.html"
    render(csv_path, html_path)
    text = html_path.read_text(encoding="utf-8")
    # Bokeh serialises labels with HTML-escaped '<' and JSON-unicode-escaped en-dash.
    assert "&lt; 100 m" in text
    assert "100\\u2013200 m" in text
    assert "&ge; 500 m" in text or "≥ 500 m" in text or "\\u2265 500 m" in text
