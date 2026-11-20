# map-digitizer

Legend-driven point-symbol detection on maps with TypeSafe Jev. See [docs/design.md](docs/design.md) for the design and [docs/research/](docs/research/) for the literature review.

## OSM rendering stack

```sh
docker compose up -d db                                   # PostGIS (also on 127.0.0.1:5433 for QGIS)
docker compose run --rm render import.sh                  # one-time: download extract, load database (~20 min)
docker compose run --rm render render.py --area freiburg_centre --zoom 17 --out /out/x.tif
docker compose run --rm render count_classes.py --zoom 17 # icon counts per class (before collision)
docker compose run --rm --no-deps render legend_sheet.py  # legend sheet + true boxes + control crops
docker compose run --rm render gt_render_diff.py --area freiburg_centre   # base render + ground-truth GeoPackage
docker compose run --rm --no-deps render gt_overlay.py /out/osm/<stem>.tif /out/osm/<stem>_gt.gpkg /out/check.png --window X Y W H
```

`./out` in the repo is `/out` in the container. Study areas are defined in `scripts/geo.py`, classes in `config/osm_classes.csv`. The extract's snapshot date is in `data/extract-info.txt`.
