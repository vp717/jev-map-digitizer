"""Rendering helpers shared by render.py, gt_render_diff.py and legend_sheet.py."""
import math, os
import numpy as np
import mapnik
from osgeo import gdal, osr

from geo import ORIGIN, lonlat_to_3857, res_at_zoom

gdal.UseExceptions()
mapnik.logger.set_severity(getattr(mapnik.severity_type, "None"))  # silence missing-font warnings
CARTO_DIR = os.environ.get("CARTO_DIR", "/opt/openstreetmap-carto")
STYLE_XML = os.path.join(CARTO_DIR, "mapnik.xml")
_fonts_done = False

def register_fonts():
    global _fonts_done
    if not _fonts_done:
        for d in ("/usr/share/fonts", os.path.join(CARTO_DIR, "fonts")):
            if os.path.isdir(d):
                mapnik.register_fonts(d)  # recurses into subfolders
        _fonts_done = True

def bbox_lonlat_to_3857(b):
    (x0, y0), (x1, y1) = lonlat_to_3857(b[0], b[1]), lonlat_to_3857(b[2], b[3])
    return x0, y0, x1, y1

def snap_bbox(minx, miny, maxx, maxy, zoom):
    """Snap outward to the zoom's web-map pixel grid (scale 1)."""
    r = res_at_zoom(zoom)
    minx = -ORIGIN + math.floor((minx + ORIGIN) / r) * r
    maxx = -ORIGIN + math.ceil((maxx + ORIGIN) / r) * r
    maxy = ORIGIN - math.floor((ORIGIN - maxy) / r) * r
    miny = ORIGIN - math.ceil((ORIGIN - miny) / r) * r
    return minx, miny, maxx, maxy

def render_array(bbox3857, zoom, scale=1.0, xml=None, buffer=256):
    """Render to an (H, W, 4) uint8 RGBA array. `xml` overrides the style (string)."""
    register_fonts()
    minx, miny, maxx, maxy = bbox3857
    res = res_at_zoom(zoom, scale)
    w, h = round((maxx - minx) / res), round((maxy - miny) / res)
    m = mapnik.Map(w, h)
    if xml is None:
        mapnik.load_map(m, STYLE_XML, False, CARTO_DIR)
    else:
        mapnik.load_map_from_string(m, xml, False, CARTO_DIR)
    m.buffer_size = buffer
    m.zoom_to_box(mapnik.Box2d(minx, miny, maxx, maxy))
    im = mapnik.Image(w, h)
    mapnik.render(m, im, scale)
    im.demultiply()
    return np.frombuffer(im.tostring(), dtype=np.uint8).reshape(h, w, 4).copy()

def write_geotiff(arr, bbox3857, path, metadata=None):
    minx, miny, maxx, maxy = bbox3857
    h, w, nb = arr.shape
    drv = gdal.GetDriverByName("GTiff")
    ds = drv.Create(path, w, h, nb, gdal.GDT_Byte,
                    ["COMPRESS=DEFLATE", "TILED=YES", "PREDICTOR=2", "PHOTOMETRIC=RGB", "ALPHA=YES"])
    ds.SetGeoTransform((minx, (maxx - minx) / w, 0, maxy, 0, -(maxy - miny) / h))
    srs = osr.SpatialReference(); srs.ImportFromEPSG(3857)
    ds.SetProjection(srs.ExportToWkt())
    for i in range(nb):
        ds.GetRasterBand(i + 1).WriteArray(arr[:, :, i])
    if metadata:
        ds.SetMetadata({k: str(v) for k, v in metadata.items()})
    ds = None
