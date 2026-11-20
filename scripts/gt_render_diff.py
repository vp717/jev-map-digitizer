#!/usr/bin/env python3
"""Ground truth by render diff.

For an area: render the base map once (this is also the evaluation image), then once
per class with that class's MarkersSymbolizers set to opacity 0. Opacity 0 still takes
part in collision/placement, so nothing else on the map moves; the changed pixels are
exactly where that class was drawn. Each connected component = one drawn icon.

Writes:  <out>/<area>_z<z>_s<scale>.tif       base render (evaluation image)
         <out>/<area>_z<z>_s<scale>_gt.gpkg   points layer "gt"
"""
import argparse, csv, os, sys, time
import xml.etree.ElementTree as ET
import numpy as np
from scipy import ndimage
from osgeo import ogr, osr
sys.path.insert(0, os.path.dirname(__file__))
from geo import AREAS, res_at_zoom
from renderlib import STYLE_XML, bbox_lonlat_to_3857, snap_bbox, render_array, write_geotiff

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
ap.add_argument("--area", choices=AREAS, required=True)
ap.add_argument("--zoom", type=int, default=17)
ap.add_argument("--scale", type=float, default=1.0)
ap.add_argument("--classes", default="/opt/mapdig/config/osm_classes.csv")
ap.add_argument("--out", default="/out/osm")
ap.add_argument("--legend-gt", default=None, help="legend _gt.json for icon sizes (default: /out/legend/legend_z<z>_s<scale>_gt.json)")
a = ap.parse_args()
os.makedirs(a.out, exist_ok=True)

classes = list(csv.DictReader(open(a.classes)))
import json
lg = a.legend_gt or f"/out/legend/legend_z{a.zoom}_s{a.scale:g}_gt.json"
icon_size = {it["file"]: (it["box"][2] - it["box"][0], it["box"][3] - it["box"][1])
             for it in json.load(open(lg))["items"]}   # (w, h) of one icon at this zoom/scale
base_xml = open(STYLE_XML).read()

def hide_class_xml(svg_file):
    root = ET.fromstring(base_xml)
    n = 0
    for ms in root.iter("MarkersSymbolizer"):
        if ms.get("file") == svg_file:
            ms.set("opacity", "0"); n += 1
    return ET.tostring(root, encoding="unicode"), n

bb = snap_bbox(*bbox_lonlat_to_3857(AREAS[a.area]), a.zoom)
res = res_at_zoom(a.zoom, a.scale)
stem = f"{a.area}_z{a.zoom}_s{a.scale:g}"
t0 = time.time()
base = render_array(bb, a.zoom, a.scale)
h, w = base.shape[:2]
write_geotiff(base, bb, f"{a.out}/{stem}.tif", {"zoom": a.zoom, "scale": a.scale, "area": a.area,
              "style": "openstreetmap-carto", "style_version": os.environ.get("CARTO_VERSION", "")})
print(f"base {w}x{h} px rendered in {time.time()-t0:.0f}s", flush=True)

gpkg = f"{a.out}/{stem}_gt.gpkg"
if os.path.exists(gpkg):
    os.remove(gpkg)
ds = ogr.GetDriverByName("GPKG").CreateDataSource(gpkg)
srs = osr.SpatialReference(); srs.ImportFromEPSG(3857)
lyr = ds.CreateLayer("gt", srs, ogr.wkbPoint)
for name, typ in [("class", ogr.OFTString), ("label", ogr.OFTString), ("grp", ogr.OFTString),
                  ("px_x", ogr.OFTReal), ("px_y", ogr.OFTReal), ("bbox_w", ogr.OFTInteger),
                  ("bbox_h", ogr.OFTInteger), ("n_px", ogr.OFTInteger), ("suspect", ogr.OFTInteger)]:
    lyr.CreateField(ogr.FieldDefn(name, typ))

summary = []
struct = np.ones((3, 3), bool)
for c in classes:
    t1 = time.time()
    xml, n_sym = hide_class_xml(c["file"])
    if n_sym == 0:
        print(f"!! {c['file']}: no MarkersSymbolizer uses this file; skipped"); continue
    hidden = render_array(bb, a.zoom, a.scale, xml=xml)
    diff = np.abs(base.astype(np.int16) - hidden.astype(np.int16)).max(axis=2) > 8
    # merge disconnected parts of one icon (e.g. a letter plus a frame) before labelling
    grown = ndimage.binary_dilation(diff, struct, iterations=max(1, round(2 * a.scale)))
    lab, n = ndimage.label(grown, struct)
    lab[~diff] = 0
    objs = ndimage.find_objects(lab)
    iw, ih = icon_size[c["file"]]
    n_drawn = n_split = n_susp = 0
    for i, sl in enumerate(objs, start=1):
        if sl is None:
            continue
        ys, xs = sl
        bw, bh = xs.stop - xs.start, ys.stop - ys.start
        # Touching icons merge into one component. Split along each axis into as many
        # icon-sized cells as fit (icons are never drawn overlapping).
        nx, ny = max(1, round(bw / (iw + 1))), max(1, round(bh / (ih + 1)))
        parts = []
        for jx in range(nx):
            for jy in range(ny):
                sub = lab[ys.start + jy * bh // ny: ys.start + (jy + 1) * bh // ny,
                          xs.start + jx * bw // nx: xs.start + (jx + 1) * bw // nx] == i
                if sub.sum() < 0.25 * (lab[sl] == i).sum() / (nx * ny):
                    continue   # mostly empty cell: not an icon
                parts.append((xs.start + (jx + 0.5) * bw / nx, ys.start + (jy + 0.5) * bh / ny,
                              bw / nx, bh / ny, int(sub.sum())))
        # anything still far outside one icon's size is flagged for manual review
        susp = int(bw / nx > 1.5 * iw + 2 or bh / ny > 1.5 * ih + 2)
        n_split += len(parts) > 1
        n_susp += susp * len(parts)
        for cx, cy, pw, ph, npx in parts:      # pixel-edge coordinates
            f = ogr.Feature(lyr.GetLayerDefn())
            for k, v in [("class", c["file"]), ("label", c["label"]), ("grp", c["group"]), ("px_x", cx),
                         ("px_y", cy), ("bbox_w", round(pw)), ("bbox_h", round(ph)),
                         ("n_px", npx), ("suspect", susp)]:
                f.SetField(k, v)
            pt = ogr.Geometry(ogr.wkbPoint); pt.AddPoint_2D(bb[0] + cx * res, bb[3] - cy * res)
            f.SetGeometry(pt); lyr.CreateFeature(f)
            n_drawn += 1
    summary.append((c["label"], n_drawn, n_split, n_susp))
    print(f"{c['label']:<20} {n_drawn:5d} drawn  {n_split:3d} split  {n_susp:3d} suspect  ({time.time()-t1:.0f}s)", flush=True)
ds = None
with open(f"{a.out}/{stem}_gt_summary.csv", "w", newline="") as fh:
    wr = csv.writer(fh); wr.writerow(["label", "drawn", "merged_split", "suspect"]); wr.writerows(summary)
print(f"wrote {gpkg}; total {sum(s[1] for s in summary)} icons in {time.time()-t0:.0f}s")
