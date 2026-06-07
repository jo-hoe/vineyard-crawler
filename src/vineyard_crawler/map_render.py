"""Interactive map renderer using Bokeh.

Reads a vineyard CSV, plots each vineyard as a coloured circle on a tile map,
and emits a self-contained HTML file with browser-side controls — sliders to
re-bucket distances and checkboxes to toggle each bucket's visibility — both
running in pure JS without a Python kernel.
"""
from __future__ import annotations

import csv
import math
from dataclasses import dataclass
from pathlib import Path

from bokeh.layouts import column, row
from bokeh.models import (
    Button,
    CheckboxGroup,
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

_VISIBLE_ALPHA: float = 0.85
_HIDDEN_ALPHA: float = 0.0


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
    bucket_indices: list[int] = []
    for p in points:
        x, y = _project_to_web_mercator(p.lat, p.lon)
        xs.append(x)
        ys.append(y)
        distances.append(p.distance_m if p.distance_m is not None else SLIDER_MAX_M)
        bucket_indices.append(_bucket_index(p.distance_m, DEFAULT_THRESHOLDS_M))

    return ColumnDataSource(
        data={
            "x": xs,
            "y": ys,
            "name": [p.name for p in points],
            "river": [p.nearest_river for p in points],
            "operator": [p.operator for p in points],
            "distance_m": distances,
            "bucket": bucket_indices,
            "color": [BUCKET_COLORS[b] for b in bucket_indices],
            "alpha": [_VISIBLE_ALPHA] * len(points),
        }
    )


def _update_callback(
    source: ColumnDataSource,
    sliders: list[Slider],
    checkboxes: CheckboxGroup,
) -> CustomJS:
    """Build the JS that recomputes bucket assignment, colour, and visibility.

    Runs whenever any slider moves OR any visibility checkbox toggles. Keeps
    the per-point bucket index in sync with the live thresholds so toggling
    visibility uses the same bucketing as the colours show.
    """
    return CustomJS(
        args={
            "source": source,
            "sliders": sliders,
            "checkboxes": checkboxes,
            "palette": list(BUCKET_COLORS),
            "visible_alpha": _VISIBLE_ALPHA,
            "hidden_alpha": _HIDDEN_ALPHA,
        },
        code="""
        const data = source.data;
        const dists = data['distance_m'];
        const buckets = data['bucket'];
        const colors = data['color'];
        const alphas = data['alpha'];
        const t = sliders.map(s => s.value).sort((a, b) => a - b);
        const active = new Set(checkboxes.active);
        for (let i = 0; i < dists.length; i++) {
            const d = dists[i];
            let b = t.length;
            for (let j = 0; j < t.length; j++) {
                if (d < t[j]) { b = j; break; }
            }
            buckets[i] = b;
            colors[i] = palette[b];
            alphas[i] = active.has(b) ? visible_alpha : hidden_alpha;
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


def _bucket_labels(thresholds: tuple[int, ...]) -> list[str]:
    """Human-readable label for each bucket — '< 100 m', '100–200 m', '≥ 500 m'."""
    labels: list[str] = [f"< {thresholds[0]} m"]
    for lo, hi in zip(thresholds[:-1], thresholds[1:]):
        labels.append(f"{lo}–{hi} m")
    labels.append(f"≥ {thresholds[-1]} m")
    return labels


def _build_visibility_checkboxes() -> CheckboxGroup:
    """All buckets visible by default."""
    return CheckboxGroup(
        labels=_bucket_labels(DEFAULT_THRESHOLDS_M),
        active=list(range(len(BUCKET_COLORS))),
        inline=True,
    )


def _legend_html() -> Div:
    return Div(
        text="""
        <div style="font-family:sans-serif;font-size:13px;">
            <strong>Distance to nearest river</strong> —
            tick / untick a bucket to hide it on the map; drag the sliders to re-bucket.
        </div>
        """,
        width=900,
    )


def _checkbox_label_html() -> Div:
    """Coloured swatches placed above the checkbox row so the colour-to-bucket
    mapping is unmistakable.  Bokeh's CheckboxGroup labels are plain text only,
    so we render the swatches in a separate Div aligned with the checkboxes.
    """
    items = "".join(
        f'<span style="display:inline-block;width:14px;height:14px;'
        f'background:{c};margin:0 6px 0 14px;vertical-align:middle;'
        f'border:1px solid #888;"></span>'
        f'<span style="font-family:sans-serif;font-size:12px;color:#555;">B{i + 1}</span>'
        for i, c in enumerate(BUCKET_COLORS)
    )
    return Div(text=f'<div>{items}</div>', width=900)


def _build_figure(source: ColumnDataSource) -> figure:
    p = figure(
        x_axis_type="mercator",
        y_axis_type="mercator",
        width=900,
        height=700,
        tools="pan,wheel_zoom,box_zoom,reset,save",
        active_scroll="wheel_zoom",
        match_aspect=True,
        title="Vineyards of Germany — coloured by distance to nearest river",
    )
    p.add_tile(xyz_providers.CartoDB.Positron)
    # fill_alpha is now data-driven so unchecked buckets vanish.
    p.scatter(
        x="x", y="y", size=7,
        fill_color="color", line_color="#222", line_width=0.5,
        fill_alpha="alpha", line_alpha="alpha",
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
    checkboxes = _build_visibility_checkboxes()

    callback = _update_callback(source, sliders, checkboxes)
    for s in sliders:
        s.js_on_change("value", callback)
    checkboxes.js_on_change("active", callback)

    reset = Button(label="Reset thresholds", button_type="default", width=160)
    reset.js_on_click(CustomJS(
        args={
            "sliders": sliders,
            "checkboxes": checkboxes,
            "default_thresholds": list(DEFAULT_THRESHOLDS_M),
            "default_active": list(range(len(BUCKET_COLORS))),
        },
        code="""
            for (let i = 0; i < sliders.length; i++) sliders[i].value = default_thresholds[i];
            checkboxes.active = default_active;
        """,
    ))

    layout = column(
        _legend_html(),
        _build_figure(source),
        row(*sliders),
        _checkbox_label_html(),
        checkboxes,
        reset,
    )

    output_file(html_path, title="Vineyards of Germany")
    save(layout)
    return len(points)
