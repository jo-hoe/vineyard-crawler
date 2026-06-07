"""Entrypoint: render an interactive map from a vineyard CSV."""
from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

# Allow running `python render_map.py` directly without installing the package.
_SRC = Path(__file__).resolve().parent / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from vineyard_crawler.map_render import render

DEFAULT_INPUT = Path("vineyards.csv")
DEFAULT_OUTPUT = Path("vineyards_map.html")

log = logging.getLogger("vineyard-crawler-map")


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="vineyard-crawler-map",
        description=(
            "Render an interactive Bokeh map from a vineyard CSV produced "
            "by main.py.  Output is a self-contained HTML file."
        ),
    )
    parser.add_argument(
        "-i", "--input",
        type=Path,
        default=DEFAULT_INPUT,
        metavar="PATH",
        help=f"input CSV path (default: {DEFAULT_INPUT})",
    )
    parser.add_argument(
        "-o", "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        metavar="PATH",
        help=f"output HTML path (default: {DEFAULT_OUTPUT})",
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="enable debug logging",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_arg_parser().parse_args(sys.argv[1:] if argv is None else argv)
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
    )
    if not args.input.exists():
        log.error("Input CSV not found: %s — run `make start` first.", args.input)
        return 1
    try:
        n = render(args.input, args.output)
    except Exception as exc:
        log.error("%s", exc)
        return 1
    log.info("Rendered %d points to %s", n, args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
