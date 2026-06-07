"""Entrypoint: fetch named German vineyards from Overpass and write to CSV."""
from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

# Allow running `python main.py` directly without installing the package.
_SRC = Path(__file__).resolve().parent / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from vineyard_crawler.bbox import GERMANY, BoundingBox
from vineyard_crawler.csv_export import write_csv
from vineyard_crawler.overpass import (
    DEFAULT_ENDPOINT,
    DEFAULT_TIMEOUT_S,
    OverpassClient,
)
from vineyard_crawler.vineyard import Vineyard, from_overpass_response

DEFAULT_OUTPUT = Path("vineyards.csv")

log = logging.getLogger("vineyard-crawler")


def _parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="vineyard-crawler",
        description=(
            "Scrape named German vineyards (Weinlagen/Einzellagen) from "
            "OpenStreetMap via the Overpass API and export them to CSV."
        ),
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help=f"output CSV path (default: {DEFAULT_OUTPUT})",
    )
    parser.add_argument(
        "--bbox",
        type=BoundingBox.parse,
        default=GERMANY,
        help=(
            "bounding box as 'south,west,north,east' "
            f"(default: Germany {GERMANY.as_overpass()})"
        ),
    )
    parser.add_argument(
        "--endpoint",
        default=DEFAULT_ENDPOINT,
        help=f"Overpass interpreter URL (default: {DEFAULT_ENDPOINT})",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=DEFAULT_TIMEOUT_S,
        help=f"Overpass server timeout in seconds (default: {DEFAULT_TIMEOUT_S})",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="enable debug logging",
    )
    return parser.parse_args(argv)


def _fetch(client: OverpassClient, bbox: BoundingBox) -> list[Vineyard]:
    log.info("Querying Overpass for vineyards in %s", bbox.as_overpass())
    payload = client.fetch(bbox)
    vineyards = from_overpass_response(payload)
    log.info("Parsed %d named vineyards from response", len(vineyards))
    return vineyards


def run(args: argparse.Namespace) -> int:
    client = OverpassClient(endpoint=args.endpoint, timeout_s=args.timeout)
    vineyards = _fetch(client, args.bbox)
    written = write_csv(vineyards, args.output)
    log.info("Wrote %d rows to %s", written, args.output)
    return 0


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(sys.argv[1:] if argv is None else argv)
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
    )
    return run(args)


if __name__ == "__main__":
    raise SystemExit(main())
