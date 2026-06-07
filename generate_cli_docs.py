"""Generate CLI.md — a markdown reference for all vineyard-crawler arguments.

Invoked by `make docs`. Introspects the live argparse parser so the output
is always in sync with the actual argument definitions.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

_SRC = Path(__file__).resolve().parent / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from main import build_arg_parser  # noqa: E402

_OUTPUT = Path(__file__).resolve().parent / "CLI.md"

_HEADER = """\
# CLI Reference

Generated from the live argument parser — do not edit by hand.

```
{usage}
```

## Arguments

| Argument | Metavar | Default | Description |
| -------- | ------- | ------- | ----------- |
"""


def _metavar(action: argparse.Action) -> str:
    if isinstance(action, argparse._StoreTrueAction):  # noqa: SLF001
        return ""
    if action.metavar:
        return f"`{action.metavar}`"
    if action.dest:
        return f"`{action.dest.upper()}`"
    return ""


def _default(action: argparse.Action) -> str:
    if action.default is None or action.default == argparse.SUPPRESS:
        return ""
    value = action.default
    # BoundingBox default: render as overpass string
    if hasattr(value, "as_overpass"):
        return f"`{value.as_overpass()}`"
    if isinstance(value, list):
        return f"`{' '.join(str(v) for v in value)}`" if value else "*(none)*"
    if isinstance(value, Path):
        return f"`{value}`"
    return f"`{value}`"


def _option_str(action: argparse.Action) -> str:
    return ", ".join(f"`{o}`" for o in action.option_strings)


def _description(action: argparse.Action) -> str:
    raw = (action.help or "").replace("\n", " ")
    return raw.replace("|", "\\|")


def generate(output: Path = _OUTPUT) -> None:
    parser = build_arg_parser()
    usage = parser.format_usage().strip()

    rows: list[str] = []
    for action in parser._actions:  # noqa: SLF001
        if isinstance(action, argparse._HelpAction):  # noqa: SLF001
            continue
        rows.append(
            f"| {_option_str(action)} "
            f"| {_metavar(action)} "
            f"| {_default(action)} "
            f"| {_description(action)} |"
        )

    output.write_text(
        _HEADER.format(usage=usage) + "\n".join(rows) + "\n",
        encoding="utf-8",
    )
    print(f"Written: {output}")


if __name__ == "__main__":
    generate()
