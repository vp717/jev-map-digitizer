#!/usr/bin/env python3
"""Draw ground-truth points over a crop of the base render, for visual checking."""
import argparse
import numpy as np
from osgeo import gdal, ogr
from PIL import Image, ImageDraw
gdal.UseExceptions()
ap = argparse.ArgumentParser()
ap.add_argument("tif"); ap.add_argument("gpkg"); ap.add_argument("out")
ap.add_argument("--window", nargs=4, type=int, metavar=("X", "Y", "W", "H"), required=True)
ap.add_argument("--zoom-factor", type=int, default=2)
a = ap.parse_args()
x, y, w, h = a.window
ds = gdal.Open(a.tif)
img = Image.fromarray(np.dstack([ds.GetRasterBand(i).ReadAsArray(x, y, w, h) for i in (1, 2, 3)]))
k = a.zoom_factor
img = img.resize((w * k, h * k), Image.NEAREST)
d = ImageDraw.Draw(img)
vds = ogr.Open(a.gpkg)  # keep a reference or the layer dies
lyr = vds.GetLayer("gt")
for f in lyr:
    px, py = f.GetField("px_x") - x, f.GetField("px_y") - y
    if 0 <= px < w and 0 <= py < h:
        col = "#ff00aa" if f.GetField("suspect") else "#00c8ff"
        bw, bh = f.GetField("bbox_w"), f.GetField("bbox_h")
        d.rectangle([(px - bw / 2) * k, (py - bh / 2) * k, (px + bw / 2) * k, (py + bh / 2) * k], outline=col, width=2)
        d.ellipse([px * k - 2, py * k - 2, px * k + 2, py * k + 2], fill=col)
img.save(a.out)
