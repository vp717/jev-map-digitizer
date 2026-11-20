"""Stage `icon-audit`: everything that renders to each class icon, and how often it occurs.

For each class icon file: every amenity-points rule that draws it at the zoom (tag filter,
colour, opacity), the distinct on-map appearances (fill, opacity), any other style or
symbolizer referencing the file, and per-rule feature counts in each area (evaluated with
openstreetmap-carto's own rules, filter-mode first, before collision dropping).
Writes <out>/icon_audit.json and <out>/icon_audit.md.
"""
import collections, csv, json, os, re

def add_args(p):
    p.add_argument("--classes", required=True)
    p.add_argument("--area", nargs=5, action="append", required=True, metavar=("NAME", "MINLON", "MINLAT", "MAXLON", "MAXLAT"))
    p.add_argument("--zoom", type=int, default=17)
    p.add_argument("--out", required=True)

def run(a):
    import xml.etree.ElementTree as ET
    import mapnik
    from mapdig.geo import scale_denominator
    from mapdig.renderlib import CARTO_DIR, STYLE_XML, bbox_lonlat_to_3857

    classes = list(csv.DictReader(open(a.classes)))
    files = {c["file"]: c for c in classes}
    sd = scale_denominator(a.zoom)
    root = ET.parse(STYLE_XML).getroot()
    other_uses = collections.defaultdict(set)
    for st in root.findall("Style"):
        for ru in st.findall("Rule"):
            for el in ru:
                if el.get("file") in files and (st.get("name"), el.tag) != ("amenity-points", "MarkersSymbolizer"):
                    other_uses[el.get("file")].add(f"{st.get('name')}/{el.tag}")

    # rules via Mapnik (same order and filters Mapnik evaluates)
    m = mapnik.Map(256, 256); mapnik.load_map(m, STYLE_XML, False, CARTO_DIR)
    style = m.find_style("amenity-points")
    layer = next(l for l in m.layers if l.name == "amenity-points")
    rules = []   # (filter, file or None, appearance, rule text) for rules active at this zoom, in order
    for ru in style.rules:
        if not (ru.min_scale <= sd < ru.max_scale):
            continue
        mk = [s.extract() for s in ru.symbols if isinstance(s.extract(), mapnik.MarkersSymbolizer)]
        f = str(mk[0].file or "").replace(CARTO_DIR + "/", "") if mk else None
        rules.append((ru.filter, f, str(ru.filter)))
    # appearance per rule from the XML (fill, opacity), matched by filter text and file
    xml_rules = [(re.sub(r"\s+", "", r_.findtext("Filter") or ""), r_.find("MarkersSymbolizer")) for r_ in
                 next(s for s in root.findall("Style") if s.get("name") == "amenity-points").findall("Rule")
                 if r_.find("MarkersSymbolizer") is not None]
    def appearance(ftxt, f):
        key = re.sub(r"\s+", "", ftxt)
        for k, ms in xml_rules:
            if ms.get("file") == f and k.replace("(", "").replace(")", "") == key.replace("(", "").replace(")", ""):
                return f"{ms.get('fill')}" + (f" @{ms.get('opacity')}" if ms.get("opacity") else "")
        return "?"
    params = dict(layer.datasource.params()); params["table"] = params["table"].replace("!scale_denominator!", repr(sd))
    ds = mapnik.Datasource(**params)
    counts = collections.defaultdict(lambda: collections.defaultdict(collections.Counter))   # file -> rule -> area
    for name, *bb in a.area:
        q = mapnik.Query(mapnik.Box2d(*bbox_lonlat_to_3857([float(v) for v in bb])))
        for fld in ds.fields():
            q.add_property_name(fld)
        for feat in ds.features(q):
            for flt, f, txt in rules:
                if flt.evaluate(feat):
                    if f in files:
                        counts[f][txt][name] += 1
                    break
    out = []
    for c in classes:
        rs = []
        for flt, f, txt in rules:
            if f != c["file"]:
                continue
            tags = re.sub(r"\[feature\]\s*=\s*'([a-z_]+)'", lambda mm: mm.group(1).replace("_", "=", 1), txt)
            rs.append({"filter": txt, "tags": tags, "appearance": appearance(txt, f),
                       "counts": dict(counts[f][txt]), "total": sum(counts[f][txt].values())})
        out.append({"label": c["label"], "file": c["file"], "rules": rs,
                    "appearances": sorted({r_["appearance"] for r_ in rs}), "other_uses": sorted(other_uses[c["file"]])})
    os.makedirs(os.path.dirname(a.out) or ".", exist_ok=True)
    json.dump(out, open(a.out + ".json", "w"), indent=1)
    lines = [f"# Icon audit (zoom {a.zoom}, openstreetmap-carto {os.environ.get('CARTO_VERSION', '')})", "",
             "Counts are features per area matched by each rule (before collision dropping).", ""]
    for o in out:
        lines.append(f"## {o['label']} — `{o['file']}` — appearances: {', '.join(o['appearances'])}")
        if o["other_uses"]:
            lines.append(f"Other uses: {', '.join(o['other_uses'])}")
        lines += ["", "| Tags (rule filter) | Appearance | " + " | ".join(n for n, *_ in a.area) + " |", "|---|---|" + "---|" * len(a.area)]
        for r_ in o["rules"]:
            lines.append(f"| `{r_['tags']}` | {r_['appearance']} | " + " | ".join(str(r_["counts"].get(n, 0)) for n, *_ in a.area) + " |")
        lines.append("")
    open(a.out + ".md", "w").write("\n".join(lines))
    print("\n".join(lines))
