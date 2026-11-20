#!/usr/bin/env python3
"""Count how many features each amenity-points icon file would be used for in an area,
by evaluating openstreetmap-carto's own rules (first matching rule with a marker, per
feature, at the zoom's scale). Counts are before collision dropping."""
import argparse, collections, csv, os, sys
import mapnik
sys.path.insert(0, os.path.dirname(__file__))
from geo import AREAS, lonlat_to_3857, res_at_zoom, scale_denominator

ap = argparse.ArgumentParser()
ap.add_argument("--zoom", type=int, default=17)
ap.add_argument("--out", default=None)
a = ap.parse_args()
a.out = a.out or f"/out/class_counts_z{a.zoom}.csv"

style_path = os.path.join(os.environ["CARTO_DIR"], "mapnik.xml")
m = mapnik.Map(256, 256)
mapnik.load_map(m, style_path, False, os.path.dirname(style_path))
layer = next(l for l in m.layers if l.name == "amenity-points")
style = m.find_style("amenity-points")
sd = scale_denominator(a.zoom)
rules = []
for ru in style.rules:
    if not (ru.min_scale <= sd < ru.max_scale):
        continue
    # filter-mode is "first": the first matching rule wins even if it draws no marker
    markers = [s.extract() for s in ru.symbols if isinstance(s.extract(), mapnik.MarkersSymbolizer)]
    rules.append((ru.filter, markers[0] if markers else None))

# This binding cannot pass a scale denominator through Query, so bake it into the SQL.
params = dict(layer.datasource.params())
params["table"] = params["table"].replace("!scale_denominator!", repr(sd))
ds = mapnik.Datasource(**params)

def sym_key(sym):
    f = str(sym.file or "").replace(os.environ["CARTO_DIR"] + "/", "")
    if not f:  # plain dot marker, no icon file
        f = f"(dot {sym.fill} w{sym.width})" if hasattr(sym, "width") else f"(dot {sym.fill})"
    return f

counts = collections.defaultdict(collections.Counter)
for area, (x0, y0, x1, y1) in AREAS.items():
    minx, miny = lonlat_to_3857(x0, y0); maxx, maxy = lonlat_to_3857(x1, y1)
    q = mapnik.Query(mapnik.Box2d(minx, miny, maxx, maxy))
    for name in ds.fields():          # Mapnik only fetches attributes that are requested
        q.add_property_name(name)
    for f in ds.features(q):
        for flt, sym in rules:
            if flt.evaluate(f):
                if sym is not None:
                    counts[sym_key(sym)][area] += 1
                break

with open(a.out, "w", newline="") as fh:
    w = csv.writer(fh); w.writerow(["file"] + list(AREAS) + ["total"])
    for fname, c in sorted(counts.items(), key=lambda kv: -sum(kv[1].values())):
        w.writerow([fname] + [c[k] for k in AREAS] + [sum(c.values())])
print(f"{len(counts)} icon files used; wrote {a.out}")
