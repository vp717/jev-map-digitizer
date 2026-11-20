"""mapdig command line: one subcommand per pipeline stage (Snakemake calls these)."""
import argparse, importlib

# subcommand -> (module, add-args function, run function, help)
STAGES = {
    "fetch":         ("mapdig.data", "add_fetch_args", "fetch", "download the OSM extract, pinned by md5"),
    "extract-info":  ("mapdig.data", "add_info_args", "extract_info", "record the extract's snapshot timestamp"),
    "import-db":     ("mapdig.data", "add_import_args", "import_db", "load the extract into PostGIS"),
    "render":        ("mapdig.render", "add_args", "run", "render an area to GeoTIFF"),
    "count-classes": ("mapdig.counts", "add_args", "run", "count icon classes per area (before collision)"),
    "legend":        ("mapdig.legend", "add_args", "run", "build the legend sheet, true boxes and control crops"),
    "groundtruth":   ("mapdig.groundtruth", "add_args", "run", "base render + render-diff ground truth"),
    "overlay":       ("mapdig.overlay", "add_args", "run", "draw ground truth over a map crop"),
    "read-legend":   ("mapdig.legend_read", "add_args", "run", "Claude Opus reads the legend; code crops symbols"),
    "demo-tile":     ("mapdig.demo", "add_args", "run", "whole Jev pipeline on one tile, with intermediate images"),
    "pilot-jev":     ("mapdig.pilot", "add_args", "run", "small Jev localisation pilot across magnifications"),
}

def main(argv=None):
    ap = argparse.ArgumentParser(prog="mapdig", description=__doc__)
    sub = ap.add_subparsers(dest="stage", required=True)
    for name, (mod, add, _, help_) in STAGES.items():
        p = sub.add_parser(name, help=help_)
        getattr(importlib.import_module(mod), add)(p)
    a = ap.parse_args(argv)
    mod, _, run, _ = STAGES[a.stage]
    getattr(importlib.import_module(mod), run)(a)

if __name__ == "__main__":
    main()
