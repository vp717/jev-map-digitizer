#!/usr/bin/env bash
# Download the Geofabrik extract (once) and load it plus openstreetmap-carto's
# external data (coastlines, etc.) into PostGIS. Safe to re-run: it reimports.
set -euo pipefail
: "${EXTRACT_URL:?set EXTRACT_URL}"
PBF="/data/$(basename "$EXTRACT_URL")"
cd "$CARTO_DIR"

if [[ ! -f "$PBF" ]]; then
  echo ">> downloading $EXTRACT_URL"
  curl -fL --retry 3 -o "$PBF.part" "$EXTRACT_URL"
  # Geofabrik no longer publishes .md5 files for every extract; verify when available.
  if curl -fsL -o "$PBF.md5" "$EXTRACT_URL.md5"; then
    (cd /data && sed "s#  .*#  $(basename "$PBF").part#" "$PBF.md5" | md5sum -c -)
  fi
  mv "$PBF.part" "$PBF"
fi
if [[ ! -f /data/extract-info.txt ]]; then
  {
    echo "url: $EXTRACT_URL"
    echo "file: $(basename "$PBF")"
    echo "file_mtime_utc: $(date -u -r "$PBF" +%FT%TZ)"
    echo "osm_replication_timestamp: $(osmium fileinfo -g header.option.osmosis_replication_timestamp "$PBF")"
    echo "md5: $(md5sum "$PBF" | cut -d' ' -f1)"
    echo "size_bytes: $(stat -c %s "$PBF")"
  } > /data/extract-info.txt
fi
cat /data/extract-info.txt

psql -v ON_ERROR_STOP=1 -c "CREATE EXTENSION IF NOT EXISTS postgis; CREATE EXTENSION IF NOT EXISTS hstore;"

echo ">> osm2pgsql import"
osm2pgsql -G --hstore --style openstreetmap-carto.style \
  --tag-transform-script openstreetmap-carto.lua \
  --cache 2000 --number-processes 4 \
  -H "$PGHOST" -U "$PGUSER" -d "$PGDATABASE" "$PBF"

echo ">> indexes and functions"
psql -v ON_ERROR_STOP=1 -f indexes.sql
psql -v ON_ERROR_STOP=1 -f functions.sql

echo ">> external data"
mkdir -p /data/external
python3 scripts/get-external-data.py -C -D /data/external \
  -H "$PGHOST" -U "$PGUSER" -w "$PGPASSWORD" -d "$PGDATABASE"

echo ">> done"
