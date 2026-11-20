"""Stage `count-classes`: how many features each amenity-points icon would mark per area.

Evaluates openstreetmap-carto's own rules (filter-mode "first", at the zoom's scale) against
the layer's features. Counts are before collision dropping; use them to choose classes."""
import collections, csv, os

def add_args(p):
    p.add_argument("--area", nargs=5, action="append", required=True,
                   metavar=("NAME", "MINLON", "MINLAT", "MAXLON", "MAXLAT"))
    p.add_argument("--zoom", type=int, required=True)
    p.add_argument("--out", required=True)

def run(a):
    import mapnik
    from mapdig.geo import scale_denominator
    from mapdig.renderlib import CARTO_DIR, STYLE_XML, bbox_lonlat_to_3857

    m = mapnik.Map(256, 256)
    mapnik.load_map(m, STYLE_XML, False, CARTO_DIR)
    layer = next(l for l in m.layers if l.name == "amenity-points")
    style = m.find_style("amenity-points")
    sd = scale_denominator(a.zoom)
    rules = []
    for ru in style.rules:
        if ru.min_scale <= sd < ru.max_scale:
            markers = [s.extract() for s in ru.symbols if isinstance(s.extract(), mapnik.MarkersSymbolizer)]
            rules.append((ru.filter, markers[0] if markers else None))   # first match wins, marker or not

    def key(sym):
        f = str(sym.file or "").replace(CARTO_DIR + "/", "")
        return f or f"(dot {sym.fill})"

    # this binding cannot pass a scale denominator through Query, so bake it into the SQL
    params = dict(layer.datasource.params())
    params["table"] = params["table"].replace("!scale_denominator!", repr(sd))
    ds = mapnik.Datasource(**params)
    names = [n for n, *_ in a.area]
    counts = collections.defaultdict(collections.Counter)
    for name, *bbox in a.area:
        q = mapnik.Query(mapnik.Box2d(*bbox_lonlat_to_3857([float(v) for v in bbox])))
        for fld in ds.fields():          # Mapnik only fetches requested attributes
            q.add_property_name(fld)
        for f in ds.features(q):
            for flt, sym in rules:
                if flt.evaluate(f):
                    if sym is not None:
                        counts[key(sym)][name] += 1
                    break
    os.makedirs(os.path.dirname(a.out) or ".", exist_ok=True)
    with open(a.out, "w", newline="") as fh:
        w = csv.writer(fh); w.writerow(["file"] + names + ["total"])
        for k, c in sorted(counts.items(), key=lambda kv: -sum(kv[1].values())):
            w.writerow([k] + [c[n] for n in names] + [sum(c.values())])
    print(f"{len(counts)} marker types; wrote {a.out}")
