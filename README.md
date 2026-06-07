# vineyard-crawler

Scrapes named German vineyard sites (Weinlagen / Einzellagen) from OpenStreetMap via the
[Overpass API](https://overpass-api.de/) and exports them to CSV.

For each vineyard the crawler emits:

| Field           | Description                                                                |
| --------------- | -------------------------------------------------------------------------- |
| `name`          | OSM `name` tag                                                             |
| `osm_type`      | `way` or `relation`                                                        |
| `osm_id`        | OSM element id                                                             |
| `latitude`      | Centroid latitude (decimal degrees)                                        |
| `longitude`     | Centroid longitude (decimal degrees)                                       |
| `area_ha`       | Approximate polygon area in hectares (Haversine / spherical-excess)        |
| `grape_variety` | OSM `grape_variety` tag (optional)                                         |
| `wikipedia`     | OSM `wikipedia` tag (optional)                                             |
| `wikidata`      | OSM `wikidata` tag (optional)                                              |

## Quick start

```bash
make init      # create venv + install dev dependencies
make test      # run the test suite
make start     # crawl Germany and write vineyards.csv
```

## CLI

```bash
python main.py --output vineyards.csv \
               --bbox 47,6,55,15 \
               --timeout 180 \
               --endpoint https://overpass-api.de/api/interpreter
```

All arguments have sensible defaults; running `python main.py` with no flags
fetches Germany and writes `vineyards.csv` in the current directory.

## OSM / Overpass policy

The crawler honours the [Overpass API usage
policy](https://operations.osmfoundation.org/policies/api/): a descriptive
`User-Agent` is sent, the query uses `out geom` so a single request is enough
(no second-pass lookup), and the configurable timeout defaults to 180 s.
