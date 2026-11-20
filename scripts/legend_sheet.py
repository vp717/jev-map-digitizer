#!/usr/bin/env python3
"""Build a printed-style legend sheet for the chosen OSM classes.

Each icon is drawn by Mapnik with the exact MarkersSymbolizer openstreetmap-carto uses
at the given zoom (same SVG, colour, size), on the style's land colour, so the legend
matches the map pixel for pixel. Labels are set in Noto Sans.

Writes:  <out>/legend_z<z>_s<scale>.png        the sheet given to the legend-reading VLM
         <out>/legend_z<z>_s<scale>_gt.json    true icon boxes on the sheet (to score the VLM)
         <out>/control_z<z>_s<scale>/<n>.png   perfect icon crops (control condition)
"""
import argparse, csv, json, os, re, sys
import xml.etree.ElementTree as ET
import numpy as np
import mapnik
from PIL import Image, ImageDraw, ImageFont
sys.path.insert(0, os.path.dirname(__file__))
from geo import scale_denominator
from renderlib import CARTO_DIR, STYLE_XML, register_fonts

ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
ap.add_argument("--zoom", type=int, default=17)
ap.add_argument("--scale", type=float, default=1.0)
ap.add_argument("--classes", default="/opt/mapdig/config/osm_classes.csv")
ap.add_argument("--out", default="/out/legend")
ap.add_argument("--columns", type=int, default=2)
a = ap.parse_args()
os.makedirs(a.out, exist_ok=True)

LAND = "#f2efe9"          # openstreetmap-carto @land-color
s = a.scale
classes = list(csv.DictReader(open(a.classes)))
sd = scale_denominator(a.zoom)

# --- find the symbolizer each class uses at this zoom (amenity-points; most generic rule) ---
root = ET.parse(STYLE_XML).getroot()
style = next(st for st in root.findall("Style") if st.get("name") == "amenity-points")
def in_range(rule):
    lo = float(rule.findtext("MinScaleDenominator") or 0)
    hi = float(rule.findtext("MaxScaleDenominator") or 1e30)
    return lo <= sd < hi
sym_for = {}
for c in classes:
    cands = []
    for rule in style.findall("Rule"):
        ms = rule.find("MarkersSymbolizer")
        if ms is not None and ms.get("file") == c["file"] and in_range(rule):
            cands.append((len(rule.findtext("Filter") or ""), dict(ms.attrib)))
    if not cands:
        sys.exit(f"{c['file']} has no marker rule at zoom {a.zoom}")
    sym_for[c["file"]] = min(cands, key=lambda t: t[0])[1]   # shortest filter = generic variant

# --- layout (all sizes in output pixels) ---
rows = -(-len(classes) // a.columns)
pad, title_h, row_h, col_w, icon_cx = round(16 * s), round(36 * s), round(26 * s), round(230 * s), round(20 * s)
W = pad * 2 + col_w * a.columns
H = pad * 2 + title_h + rows * row_h
pos = []
for i, c in enumerate(classes):
    col, row = divmod(i, rows)
    x = pad + col * col_w + icon_cx
    y = pad + title_h + row * row_h + row_h // 2
    pos.append((x, y))

# --- draw icons with Mapnik in a pixel coordinate system (1 map unit = 1 output px) ---
merc = "+proj=merc +a=6378137 +b=6378137 +lat_ts=0 +lon_0=0 +x_0=0 +y_0=0 +k=1 +units=m +nadgrids=@null +no_defs"
rules = []
for i, c in enumerate(classes):
    attrs = dict(sym_for[c["file"]], **{"allow-overlap": "true", "ignore-placement": "true"})
    attr_s = " ".join(f'{k}="{v}"' for k, v in attrs.items())
    rules.append(f"<Rule><Filter>[cls] = {i}</Filter><MarkersSymbolizer {attr_s}/></Rule>")
csv_rows = "\n".join(f'"POINT({x} {H - y})",{i}' for i, (x, y) in enumerate(pos))
xml = f"""<Map srs="{merc}" background-color="{LAND}">
<Style name="legend">{''.join(rules)}</Style>
<Layer name="icons" srs="{merc}"><StyleName>legend</StyleName>
<Datasource><Parameter name="type">csv</Parameter><Parameter name="inline">wkt,cls
{csv_rows}</Parameter></Datasource></Layer></Map>"""
register_fonts()
m = mapnik.Map(W, H)
mapnik.load_map_from_string(m, xml, False, CARTO_DIR)
m.zoom_to_box(mapnik.Box2d(0, 0, W, H))
im = mapnik.Image(W, H)
mapnik.render(m, im, s)
im.demultiply()
arr = np.frombuffer(im.tostring(), dtype=np.uint8).reshape(H, W, 4).copy()

# --- true icon boxes: non-background pixels inside each icon cell ---
bg = np.array(Image.new("RGB", (1, 1), LAND).getpixel((0, 0)))
gt, half = [], round(row_h * 0.5)
stem = f"z{a.zoom}_s{s:g}"
ctrl_dir = f"{a.out}/control_{stem}"; os.makedirs(ctrl_dir, exist_ok=True)
for i, (c, (x, y)) in enumerate(zip(classes, pos)):
    cell = arr[y - half:y + half, x - half:x + half, :3].astype(int)
    ys, xs = np.nonzero(np.abs(cell - bg).max(axis=2) > 8)
    x0, y0 = int(xs.min()) + x - half, int(ys.min()) + y - half
    x1, y1 = int(xs.max()) + x - half + 1, int(ys.max()) + y - half + 1
    gt.append({"index": i, "label": c["label"], "file": c["file"], "group": c["group"],
               "anchor": [x, y], "box": [x0, y0, x1, y1], "symbolizer": sym_for[c["file"]]})
    slug = re.sub(r"[^a-z0-9]+", "_", c["label"].lower()).strip("_")
    Image.fromarray(arr[y0:y1, x0:x1, :3]).save(f"{ctrl_dir}/{i:02d}_{slug}.png")

# --- labels and title ---
img = Image.fromarray(arr[:, :, :3])
d = ImageDraw.Draw(img)
fdir = "/usr/share/fonts/truetype/noto"
f_lab = ImageFont.truetype(f"{fdir}/NotoSans-Regular.ttf", round(13 * s))
f_tit = ImageFont.truetype(f"{fdir}/NotoSans-Bold.ttf", round(17 * s))
d.text((pad, pad), "Legend", font=f_tit, fill="#222222")
for c, (x, y) in zip(classes, pos):
    d.text((x + round(18 * s), y), c["label"], font=f_lab, fill="#222222", anchor="lm")
img.save(f"{a.out}/legend_{stem}.png")
json.dump({"image": f"legend_{stem}.png", "size": [W, H], "zoom": a.zoom, "scale": s, "items": gt},
          open(f"{a.out}/legend_{stem}_gt.json", "w"), indent=1)
print(f"legend {W}x{H} px, {len(classes)} items -> {a.out}/legend_{stem}.png")
for g in gt:
    print(f"  {g['label']:<20} box {g['box']}  fill {g['symbolizer'].get('fill')}")
