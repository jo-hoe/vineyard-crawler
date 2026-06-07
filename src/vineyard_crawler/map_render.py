"""Interactive map renderer using Bokeh.

Reads a vineyard CSV, plots each vineyard as a coloured circle on a tile map,
and emits a self-contained HTML file with browser-side sliders that re-bucket
distances live without re-running Python.
"""
from __future__ import annotations

import csv
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from bokeh.layouts import column, row
from bokeh.models import (
    Button,
    ColumnDataSource,
    CustomJS,
    Div,
    HoverTool,
    Slider,
)
from bokeh.plotting import figure, output_file, save
from xyzservices import providers as xyz_providers

# Default bucket boundaries in metres — five buckets means four boundaries.
DEFAULT_THRESHOLDS_M: tuple[int, int, int, int] = (100, 200, 300, 500)

# Maximum slider value.  Distances beyond this are considered "very far"; clipping
# keeps the linear sliders usable at the low end where most points cluster.
SLIDER_MAX_M: int = 10_000

# Green (closest) → red (farthest).  One colour per bucket; five buckets.
BUCKET_COLORS: tuple[str, ...] = (
    "#1a9850",  # very close — saturated green
    "#91cf60",  # close — light green
    "#fee08b",  # medium — yellow
    "#fc8d59",  # far — orange
    "#d73027",  # very far — saturated red
)


@dataclass(frozen=True)
class _MapPoint:
    name: str
    lat: float
    lon: float
    distance_m: int | None
    nearest_river: str
    operator: str


def _read_points(csv_path: Path) -> list[_MapPoint]:
    with csv_path.open(encoding="utf-8", newline="") as fh:
        reader = csv.DictReader(fh)
        return [
            _MapPoint(
                name=row["name"],
                lat=float(row["latitude"]),
                lon=float(row["longitude"]),
                distance_m=int(row["river_distance_m"]) if row["river_distance_m"] else None,
                nearest_river=row["nearest_river"],
                operator=row["operator"],
            )
            for row in reader
        ]


def _project_to_web_mercator(lat: float, lon: float) -> tuple[float, float]:
    """WGS84 lat/lon → Web Mercator metres (EPSG:3857)."""
    radius = 6_378_137.0
    x = lon * radius * math.pi / 180.0
    y = math.log(math.tan(math.pi / 4 + math.radians(lat) / 2)) * radius
    return x, y


def _bucket_index(distance_m: int | None, thresholds: tuple[int, ...]) -> int:
    """Map a distance to a bucket index 0..len(thresholds).

    None (no enrichment) lands in the last bucket so unenriched points are
    visually distinguishable as "unknown distance".
    """
    if distance_m is None:
        return len(thresholds)
    for i, threshold in enumerate(thresholds):
        if distance_m < threshold:
            return i
    return len(thresholds)


def _build_source(points: list[_MapPoint]) -> ColumnDataSource:
    xs: list[float] = []
    ys: list[float] = []
    distances: list[int] = []
    for p in points:
        x, y = _project_to_web_mercator(p.lat, p.lon)
        xs.append(x)
        ys.append(y)
        distances.append(p.distance_m if p.distance_m is not None else SLIDER_MAX_M)

    return ColumnDataSource(
        data={
            "x": xs,
            "y": ys,
            "name": [p.name for p in points],
            "river": [p.nearest_river for p in points],
            "operator": [p.operator for p in points],
            "distance_m": distances,
            "color": [
                BUCKET_COLORS[_bucket_index(p.distance_m, DEFAULT_THRESHOLDS_M)]
                for p in points
            ],
        }
    )


def _slider_callback(
    source: ColumnDataSource,
    sliders: list[Slider],
) -> CustomJS:
    """Build the JS that re-colours every point when any slider moves."""
    return CustomJS(
        args={"source": source, "sliders": sliders, "palette": list(BUCKET_COLORS)},
        code="""
        const data = source.data;
        const dists = data['distance_m'];
        const colors = data['color'];
        const t = sliders.map(s => s.value).sort((a, b) => a - b);
        for (let i = 0; i < dists.length; i++) {
            const d = dists[i];
            let bucket = t.length;
            for (let j = 0; j < t.length; j++) {
                if (d < t[j]) { bucket = j; break; }
            }
            colors[i] = palette[bucket];
        }
        source.change.emit();
        """,
    )


def _build_sliders(thresholds: tuple[int, ...]) -> list[Slider]:
    return [
        Slider(
            start=0,
            end=SLIDER_MAX_M,
            value=t,
            step=10,
            title=f"Bucket {i + 1}/{len(thresholds) + 1} threshold (m)",
            width=400,
        )
        for i, t in enumerate(thresholds)
    ]


def _legend_html() -> Div:
    items = "".join(
        f'<span style="display:inline-block;width:14px;height:14px;'
        f'background:{c};margin-right:6px;vertical-align:middle;border:1px solid #888;"></span>'
        f'<span style="margin-right:18px;">Bucket&nbsp;{i + 1}</span>'
        for i, c in enumerate(BUCKET_COLORS)
    )
    return Div(
        text=f"""
        <div style="font-family:sans-serif;font-size:13px;">
            <strong>Distance to nearest river</strong> — drag sliders to re-bucket.
            <div style="margin-top:8px;">{items}</div>
        </div>
        """,
        width=900,
    )


def _build_figure(source: ColumnDataSource) -> figure:
    p = figure(
        x_axis_type="mercator",
        y_axis_type="mercator",
        width=900,
        height=700,
        tools="pan,wheel_zoom,box_zoom,reset,save",
        active_scroll="wheel_zoom",
        title="Vineyards of Germany — coloured by distance to nearest river",
    )
    p.add_tile(xyz_providers.CartoDB.Positron)
    p.scatter(
        x="x", y="y", size=7,
        fill_color="color", line_color="#222", line_width=0.5,
        fill_alpha=0.85,
        source=source,
    )
    p.add_tools(HoverTool(tooltips=[
        ("Name", "@name"),
        ("River", "@river"),
        ("Distance (m)", "@distance_m"),
        ("Operator", "@operator"),
    ]))
    return p


def render(csv_path: Path, html_path: Path) -> int:
    """Render *csv_path* into a self-contained interactive HTML map at *html_path*.

    Returns the number of points plotted.
    """
    points = _read_points(csv_path)
    source = _build_source(points)
    sliders = _build_sliders(DEFAULT_THRESHOLDS_M)

    callback = _slider_callback(source, sliders)
    for s in sliders:
        s.js_on_change("value", callback)

    reset = Button(label="Reset thresholds", button_type="default", width=160)
    reset.js_on_click(CustomJS(
        args={"sliders": sliders, "defaults": list(DEFAULT_THRESHOLDS_M)},
        code="for (let i = 0; i < sliders.length; i++) sliders[i].value = defaults[i];",
    ))

    layout = column(
        _legend_html(),
        _build_figure(source),
        row(*sliders),
        reset,
    )

    output_file(html_path, title="Vineyards of Germany")
    save(layout)
    return len(points)
