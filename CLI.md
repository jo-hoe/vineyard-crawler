# CLI Reference

Generated from the live argument parser — do not edit by hand.

```
usage: vineyard-crawler [-h] [-o PATH] [--bbox S,W,N,E] [--endpoint URL] [--timeout SECONDS] [--waterway [TYPE ...]] [-v]
```

## Arguments

| Argument | Metavar | Default | Description |
| -------- | ------- | ------- | ----------- |
| `-o`, `--output` | `PATH` | `vineyards.csv` | output CSV path (default: vineyards.csv) |
| `--bbox` | `S,W,N,E` | `47.0,6.0,55.0,15.0` | bounding box as 'south,west,north,east' (default: Germany 47.0,6.0,55.0,15.0) |
| `--endpoint` | `URL` | `https://overpass-api.de/api/interpreter` | Overpass interpreter URL (default: https://overpass-api.de/api/interpreter) |
| `--timeout` | `SECONDS` | `180` | Overpass server timeout in seconds (default: 180) |
| `--waterway` | `TYPE` | `river` | waterway OSM types to fetch for river-distance enrichment (default: river). Pass --waterway river stream to include streams. Pass --waterway with no arguments to skip enrichment entirely. |
| `-v`, `--verbose` |  | `False` | enable debug logging |
