"""Stage `legend`: a printed-style legend sheet for the chosen classes.

Each icon is drawn by Mapnik with the exact MarkersSymbolizer openstreetmap-carto uses at
the zoom (same SVG, colour, size), on the land colour, so the legend matches the map pixel
for pixel. Writes into --outdir:
  sheet.png       the sheet given to the legend-reading VLM
  sheet_gt.json   true icon boxes on the sheet (scores the VLM; gives icon sizes to groundtruth)
  control/        perfect icon crops (control condition)
  manifest.json
"""
import csv, json, os, re, sys

def add_args(p):
    p.add_argument("--classes", required=True)
    p.add_argument("--zoom", type=int, required=True)
    p.add_argument("--scale", type=float, required=True)
    p.add_argument("--columns", type=int, default=2)
    p.add_argument("--outdir", required=True)

def run(a):
    import xml.etree.ElementTree as ET
    import numpy as np
    import mapnik
    from PIL import Image, ImageDraw, ImageFont
    from mapdig.geo import scale_denominator
    from mapdig.manifest import Manifest
    from mapdig.renderlib import CARTO_DIR, LAND_COLOUR, STYLE_XML, register_fonts

    m_ = Manifest("legend", {"zoom": a.zoom, "scale": a.scale, "columns": a.columns}, inputs=[a.classes])
    os.makedirs(a.outdir, exist_ok=True)
    s = a.scale
    classes = list(csv.DictReader(open(a.classes)))
    sd = scale_denominator(a.zoom)

    # the symbolizer each class uses at this zoom (amenity-points; most generic rule)
    root = ET.parse(STYLE_XML).getroot()
    style = next(st for st in root.findall("Style") if st.get("name") == "amenity-points")
    def in_range(rule):
        return float(rule.findtext("MinScaleDenominator") or 0) <= sd < float(rule.findtext("MaxScaleDenominator") or 1e30)
    sym_for = {}
    for c in classes:
        cands = [(len(r.findtext("Filter") or ""), dict(r.find("MarkersSymbolizer").attrib))
                 for r in style.findall("Rule")
                 if r.find("MarkersSymbolizer") is not None and r.find("MarkersSymbolizer").get("file") == c["file"]
                 and in_range(r)]
        if not cands:
            sys.exit(f"{c['file']} has no marker rule at zoom {a.zoom}")
        sym_for[c["file"]] = min(cands, key=lambda t: t[0])[1]   # shortest filter = generic variant

    # layout in output pixels
    rows = -(-len(classes) // a.columns)
    pad, title_h, row_h, col_w, icon_cx = (round(v * s) for v in (16, 36, 26, 230, 20))
    W, H = pad * 2 + col_w * a.columns, pad * 2 + title_h + rows * row_h
    pos = []
    for i in range(len(classes)):
        col, row = divmod(i, rows)
        pos.append((pad + col * col_w + icon_cx, pad + title_h + row * row_h + row_h // 2))

    # icons via Mapnik in a pixel coordinate system (1 map unit = 1 output px)
    merc = "+proj=merc +a=6378137 +b=6378137 +lat_ts=0 +lon_0=0 +x_0=0 +y_0=0 +k=1 +units=m +nadgrids=@null +no_defs"
    rules = []
    for i, c in enumerate(classes):
        attrs = dict(sym_for[c["file"]], **{"allow-overlap": "true", "ignore-placement": "true"})
        rules.append(f"<Rule><Filter>[cls] = {i}</Filter><MarkersSymbolizer "
                     + " ".join(f'{k}="{v}"' for k, v in attrs.items()) + "/></Rule>")
    csv_rows = "\n".join(f'"POINT({x} {H - y})",{i}' for i, (x, y) in enumerate(pos))
    xml = f"""<Map srs="{merc}" background-color="{LAND_COLOUR}">
<Style name="legend">{''.join(rules)}</Style>
<Layer name="icons" srs="{merc}"><StyleName>legend</StyleName>
<Datasource><Parameter name="type">csv</Parameter><Parameter name="inline">wkt,cls
{csv_rows}</Parameter></Datasource></Layer></Map>"""
    register_fonts()
    mp = mapnik.Map(W, H)
    mapnik.load_map_from_string(mp, xml, False, CARTO_DIR)
    mp.zoom_to_box(mapnik.Box2d(0, 0, W, H))
    im = mapnik.Image(W, H)
    mapnik.render(mp, im, s)
    im.demultiply()
    arr = np.frombuffer(im.tostring(), dtype=np.uint8).reshape(H, W, 4).copy()

    # true icon boxes: non-background pixels inside each icon cell
    bg = np.array(Image.new("RGB", (1, 1), LAND_COLOUR).getpixel((0, 0)))
    half, gt = round(row_h * 0.5), []
    ctrl = os.path.join(a.outdir, "control"); os.makedirs(ctrl, exist_ok=True)
    for i, (c, (x, y)) in enumerate(zip(classes, pos)):
        cell = arr[y - half:y + half, x - half:x + half, :3].astype(int)
        ys, xs = np.nonzero(np.abs(cell - bg).max(axis=2) > 8)
        x0, y0 = int(xs.min()) + x - half, int(ys.min()) + y - half
        x1, y1 = int(xs.max()) + x - half + 1, int(ys.max()) + y - half + 1
        gt.append({"index": i, "label": c["label"], "file": c["file"], "group": c["group"],
                   "anchor": [x, y], "box": [x0, y0, x1, y1], "symbolizer": sym_for[c["file"]]})
        slug = re.sub(r"[^a-z0-9]+", "_", c["label"].lower()).strip("_")
        Image.fromarray(arr[y0:y1, x0:x1, :3]).save(os.path.join(ctrl, f"{i:02d}_{slug}.png"))

    img = Image.fromarray(arr[:, :, :3])
    d = ImageDraw.Draw(img)
    fdir = "/usr/share/fonts/truetype/noto"
    f_lab = ImageFont.truetype(f"{fdir}/NotoSans-Regular.ttf", round(13 * s))
    f_tit = ImageFont.truetype(f"{fdir}/NotoSans-Bold.ttf", round(17 * s))
    d.text((pad, pad), "Legend", font=f_tit, fill="#222222")
    for c, (x, y) in zip(classes, pos):
        d.text((x + round(18 * s), y), c["label"], font=f_lab, fill="#222222", anchor="lm")
    img.save(os.path.join(a.outdir, "sheet.png"))
    with open(os.path.join(a.outdir, "sheet_gt.json"), "w") as fh:
        json.dump({"image": "sheet.png", "size": [W, H], "zoom": a.zoom, "scale": s, "items": gt}, fh, indent=1)
    m_.write(os.path.join(a.outdir, "manifest.json"), outputs=["sheet.png", "sheet_gt.json", "control/"])
    print(f"legend {W}x{H} px, {len(classes)} items -> {a.outdir}")
