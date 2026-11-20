"""Command `overlay`: draw ground-truth points over a crop of a map, for visual checks."""

def add_args(p):
    p.add_argument("tif"); p.add_argument("gpkg"); p.add_argument("out")
    p.add_argument("--window", nargs=4, type=int, metavar=("X", "Y", "W", "H"), required=True)
    p.add_argument("--magnify", type=int, default=2)

def run(a):
    import numpy as np
    from osgeo import gdal, ogr
    from PIL import Image, ImageDraw
    gdal.UseExceptions()
    x, y, w, h = a.window
    ds = gdal.Open(a.tif)
    img = Image.fromarray(np.dstack([ds.GetRasterBand(i).ReadAsArray(x, y, w, h) for i in (1, 2, 3)]))
    k = a.magnify
    img = img.resize((w * k, h * k), Image.NEAREST)
    d = ImageDraw.Draw(img)
    vds = ogr.Open(a.gpkg)   # keep a reference or the layer is freed
    for f in vds.GetLayer("gt"):
        px, py = f.GetField("px_x") - x, f.GetField("px_y") - y
        if 0 <= px < w and 0 <= py < h:
            col = "#ff00aa" if f.GetField("suspect") else "#00c8ff"
            bw, bh = f.GetField("bbox_w"), f.GetField("bbox_h")
            d.rectangle([(px - bw / 2) * k, (py - bh / 2) * k, (px + bw / 2) * k, (py + bh / 2) * k], outline=col, width=2)
    img.save(a.out)
    print(a.out)
