"""Stages `fetch`, `extract-info`, `import-db`: the OSM extract and the rendering database."""
import json, os, subprocess, sys, urllib.request

from mapdig.manifest import Manifest, file_md5

def add_fetch_args(p):
    p.add_argument("--url", required=True)
    p.add_argument("--md5", required=True, help="expected md5; the fetch fails on mismatch")
    p.add_argument("--out", required=True)

def fetch(a):
    """Download the extract. 'latest' URLs change daily, so the md5 pins the snapshot."""
    if os.path.exists(a.out) and file_md5(a.out) == a.md5:
        print(f"{a.out} already present with md5 {a.md5}")
        return
    os.makedirs(os.path.dirname(a.out) or ".", exist_ok=True)
    part = a.out + ".part"
    print(f"downloading {a.url}", flush=True)
    urllib.request.urlretrieve(a.url, part)
    got = file_md5(part)
    if got != a.md5:
        sys.exit(f"md5 mismatch for {a.url}: expected {a.md5}, got {got}. The 'latest' extract has moved on; "
                 f"update data.extract_md5 in the experiment config (this changes every downstream result), "
                 f"or restore the archived extract.")
    os.replace(part, a.out)

def add_info_args(p):
    p.add_argument("--pbf", required=True)
    p.add_argument("--url", required=True)
    p.add_argument("--out", required=True)

def extract_info(a):
    ts = subprocess.run(["osmium", "fileinfo", "-g", "header.option.osmosis_replication_timestamp", a.pbf],
                        capture_output=True, text=True, check=True).stdout.strip()
    info = {"url": a.url, "file": os.path.basename(a.pbf), "md5": file_md5(a.pbf),
            "size_bytes": os.path.getsize(a.pbf), "osm_replication_timestamp": ts}
    with open(a.out, "w") as fh:
        json.dump(info, fh, indent=1)
    print(json.dumps(info, indent=1))

def add_import_args(p):
    p.add_argument("--pbf", required=True)
    p.add_argument("--style-version", required=True, help="must match the render image's openstreetmap-carto")
    p.add_argument("--external-cache", default="data/external")
    p.add_argument("--out", required=True, help="stamp file written after a successful import")

def _psql(sql=None, file=None, capture=False):
    cmd = ["psql", "-v", "ON_ERROR_STOP=1", "-qAt"] + (["-c", sql] if sql else ["-f", file])
    r = subprocess.run(cmd, check=True, capture_output=capture, text=True)
    return r.stdout.strip() if capture else None

def import_db(a):
    """Load the extract with osm2pgsql + openstreetmap-carto's indexes, functions and external data.

    Skips the import when the database already holds this exact extract and style (stamp table)."""
    carto = os.environ["CARTO_DIR"]
    image_style = os.environ.get("CARTO_VERSION", "")
    if image_style != a.style_version:
        sys.exit(f"config wants openstreetmap-carto {a.style_version} but the render image has {image_style}")
    md5 = file_md5(a.pbf)
    m = Manifest("import-db", {"style_version": a.style_version, "pbf_md5": md5}, inputs=[a.pbf])
    _psql("CREATE EXTENSION IF NOT EXISTS postgis; CREATE EXTENSION IF NOT EXISTS hstore; "
          "CREATE TABLE IF NOT EXISTS mapdig_import (pbf_md5 text, style_version text, done_utc timestamptz)")
    stamp = _psql("SELECT pbf_md5 || ' ' || style_version FROM mapdig_import ORDER BY done_utc DESC LIMIT 1",
                  capture=True)
    if stamp == f"{md5} {a.style_version}":
        print("database already holds this extract and style; skipping import")
        m.extra["skipped"] = True
    else:
        env = dict(os.environ)
        subprocess.run(["osm2pgsql", "-G", "--hstore", "--style", "openstreetmap-carto.style",
                        "--tag-transform-script", "openstreetmap-carto.lua", "--cache", "2000",
                        "--number-processes", "4", "-H", env["PGHOST"], "-U", env["PGUSER"],
                        "-d", env["PGDATABASE"], os.path.abspath(a.pbf)], cwd=carto, check=True)
        _psql(file=os.path.join(carto, "indexes.sql"))
        _psql(file=os.path.join(carto, "functions.sql"))
        os.makedirs(a.external_cache, exist_ok=True)
        subprocess.run([sys.executable, "scripts/get-external-data.py", "-C", "-D", os.path.abspath(a.external_cache),
                        "-H", env["PGHOST"], "-U", env["PGUSER"], "-w", env["PGPASSWORD"], "-d", env["PGDATABASE"]],
                       cwd=carto, check=True)
        _psql(f"TRUNCATE mapdig_import; INSERT INTO mapdig_import VALUES ('{md5}', '{a.style_version}', now())")
    m.write(a.out, outputs=[])
