"""Entrypoint: fetch named German vineyards from Overpass and write to CSV."""
from __future__ import annotations

import argparse
import dataclasses
import logging
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

# Allow running `python main.py` directly without installing the package.
_SRC = Path(__file__).resolve().parent / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from vineyard_crawler.bbox import GERMANY, BoundingBox
from vineyard_crawler.csv_export import write_csv
from vineyard_crawler.overpass import DEFAULT_ENDPOINT, DEFAULT_TIMEOUT_S, MAX_CONCURRENT_REQUESTS, OverpassClient
from vineyard_crawler.proximity import nearest_waterway
from vineyard_crawler.vineyard import Vineyard, from_overpass_response
from vineyard_crawler.waterway import DEFAULT_WATERWAY_TYPES, WaterwayArrays, fetch_waterways

DEFAULT_OUTPUT = Path("vineyards.csv")

log = logging.getLogger("vineyard-crawler")


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="vineyard-crawler",
        description=(
            "Scrape named German vineyards (Weinlagen/Einzellagen) from "
            "OpenStreetMap via the Overpass API and export them to CSV."
        ),
    )
    parser.add_argument(
        "-o", "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        metavar="PATH",
        help=f"output CSV path (default: {DEFAULT_OUTPUT})",
    )
    parser.add_argument(
        "--bbox",
        type=BoundingBox.parse,
        default=GERMANY,
        metavar="S,W,N,E",
        help=(
            "bounding box as 'south,west,north,east' "
            f"(default: Germany {GERMANY.as_overpass()})"
        ),
    )
    parser.add_argument(
        "--endpoint",
        default=DEFAULT_ENDPOINT,
        metavar="URL",
        help=f"Overpass interpreter URL (default: {DEFAULT_ENDPOINT})",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=DEFAULT_TIMEOUT_S,
        metavar="SECONDS",
        help=f"Overpass server timeout in seconds (default: {DEFAULT_TIMEOUT_S})",
    )
    parser.add_argument(
        "--waterway",
        nargs="*",
        default=list(DEFAULT_WATERWAY_TYPES),
        metavar="TYPE",
        help=(
            "waterway OSM types to fetch for river-distance enrichment "
            f"(default: {' '.join(DEFAULT_WATERWAY_TYPES)}). "
            "Pass --waterway river stream to include streams. "
            "Pass --waterway with no arguments to skip enrichment entirely."
        ),
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="enable debug logging",
    )
    return parser


def _fetch_vineyards(client: OverpassClient, bbox: BoundingBox) -> list[Vineyard]:
    log.info("Querying Overpass for vineyards in %s", bbox.as_overpass())
    payload = client.fetch(bbox)
    vineyards = from_overpass_response(payload)
    log.info("Parsed %d named vineyards from response", len(vineyards))
    return vineyards


def _fetch_waterways(
    client: OverpassClient,
    bbox: BoundingBox,
    waterway_types: list[str],
) -> WaterwayArrays:
    log.info(
        "Querying Overpass for waterways (%s) in %s",
        ", ".join(waterway_types),
        bbox.as_overpass(),
    )
    arrays = fetch_waterways(client, bbox, waterway_types)
    log.info("Loaded %d waterway vertices", arrays.size)
    return arrays


def _fetch_parallel(
    client: OverpassClient,
    bbox: BoundingBox,
    waterway_types: list[str],
) -> tuple[list[Vineyard], WaterwayArrays]:
    """Fire the vineyard and waterway Overpass queries concurrently.

    The Overpass API grants MAX_CONCURRENT_REQUESTS (2) slots per IP.
    Both queries are independent so we use both slots in parallel to halve
    wall-clock time. The shared semaphore in OverpassClient.post_query
    ensures we never exceed the slot limit even if more threads are added.
    https://dev.overpass-api.de/overpass-doc/en/preface/commons.html
    """
    with ThreadPoolExecutor(max_workers=MAX_CONCURRENT_REQUESTS) as executor:
        future_vineyards = executor.submit(_fetch_vineyards, client, bbox)
        future_waterways = executor.submit(_fetch_waterways, client, bbox, waterway_types)
        vineyards = future_vineyards.result()
        arrays = future_waterways.result()
    return vineyards, arrays


def _enrich_with_rivers(
    vineyards: list[Vineyard],
    arrays: WaterwayArrays,
) -> list[Vineyard]:
    log.info("Computing nearest river for each vineyard boundary")
    enriched: list[Vineyard] = []
    for v in vineyards:
        result = nearest_waterway(v.boundary_points, arrays)
        if result is not None:
            enriched.append(
                dataclasses.replace(
                    v,
                    nearest_river=result.nearest_river,
                    river_distance_m=result.river_distance_m,
                )
            )
        else:
            enriched.append(v)
    log.info("River-distance enrichment complete")
    return enriched


def run(args: argparse.Namespace) -> int:
    client = OverpassClient(endpoint=args.endpoint, timeout_s=args.timeout)
    try:
        if args.waterway:
            vineyards, arrays = _fetch_parallel(client, args.bbox, args.waterway)
            vineyards = _enrich_with_rivers(vineyards, arrays)
        else:
            log.info("Skipping river-distance enrichment (no --waterway types given)")
            vineyards = _fetch_vineyards(client, args.bbox)
        written = write_csv(vineyards, args.output)
    except Exception as exc:
        log.error("%s", exc)
        return 1
    log.info("Wrote %d rows to %s", written, args.output)
    return 0


def main(argv: list[str] | None = None) -> int:
    args = build_arg_parser().parse_args(sys.argv[1:] if argv is None else argv)
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
    )
    return run(args)


if __name__ == "__main__":
    raise SystemExit(main())


DEFAULT_OUTPUT = Path("vineyards.csv")

log = logging.getLogger("vineyard-crawler")


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="vineyard-crawler",
        description=(
            "Scrape named German vineyards (Weinlagen/Einzellagen) from "
            "OpenStreetMap via the Overpass API and export them to CSV."
        ),
    )
    parser.add_argument(
        "-o", "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        metavar="PATH",
        help=f"output CSV path (default: {DEFAULT_OUTPUT})",
    )
    parser.add_argument(
        "--bbox",
        type=BoundingBox.parse,
        default=GERMANY,
        metavar="S,W,N,E",
        help=(
            "bounding box as 'south,west,north,east' "
            f"(default: Germany {GERMANY.as_overpass()})"
        ),
    )
    parser.add_argument(
        "--endpoint",
        default=DEFAULT_ENDPOINT,
        metavar="URL",
        help=f"Overpass interpreter URL (default: {DEFAULT_ENDPOINT})",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=DEFAULT_TIMEOUT_S,
        metavar="SECONDS",
        help=f"Overpass server timeout in seconds (default: {DEFAULT_TIMEOUT_S})",
    )
    parser.add_argument(
        "--waterway",
        nargs="*",
        default=list(DEFAULT_WATERWAY_TYPES),
        metavar="TYPE",
        help=(
            "waterway OSM types to fetch for river-distance enrichment "
            f"(default: {' '.join(DEFAULT_WATERWAY_TYPES)}). "
            "Pass --waterway river stream to include streams. "
            "Pass --waterway with no arguments to skip enrichment entirely."
        ),
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="enable debug logging",
    )
    return parser


def _fetch_vineyards(client: OverpassClient, bbox: BoundingBox) -> list[Vineyard]:
    log.info("Querying Overpass for vineyards in %s", bbox.as_overpass())
    payload = client.fetch(bbox)
    vineyards = from_overpass_response(payload)
    log.info("Parsed %d named vineyards from response", len(vineyards))
    return vineyards


def _enrich_with_rivers(
    vineyards: list[Vineyard],
    client: OverpassClient,
    bbox: BoundingBox,
    waterway_types: list[str],
) -> list[Vineyard]:
    log.info(
        "Querying Overpass for waterways (%s) in %s",
        ", ".join(waterway_types),
        bbox.as_overpass(),
    )
    arrays = fetch_waterways(client, bbox, waterway_types)
    log.info("Loaded %d waterway vertices", arrays.size)

    enriched: list[Vineyard] = []
    for v in vineyards:
        result = nearest_waterway(v.boundary_points, arrays)
        if result is not None:
            enriched.append(
                dataclasses.replace(
                    v,
                    nearest_river=result.nearest_river,
                    river_distance_m=result.river_distance_m,
                )
            )
        else:
            enriched.append(v)
    log.info("River-distance enrichment complete")
    return enriched


def run(args: argparse.Namespace) -> int:
    client = OverpassClient(endpoint=args.endpoint, timeout_s=args.timeout)
    try:
        vineyards = _fetch_vineyards(client, args.bbox)
        if args.waterway:
            vineyards = _enrich_with_rivers(vineyards, client, args.bbox, args.waterway)
        else:
            log.info("Skipping river-distance enrichment (no --waterway types given)")
        written = write_csv(vineyards, args.output)
    except Exception as exc:
        log.error("%s", exc)
        return 1
    log.info("Wrote %d rows to %s", written, args.output)
    return 0


def main(argv: list[str] | None = None) -> int:
    args = build_arg_parser().parse_args(sys.argv[1:] if argv is None else argv)
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
    )
    return run(args)


if __name__ == "__main__":
    raise SystemExit(main())
