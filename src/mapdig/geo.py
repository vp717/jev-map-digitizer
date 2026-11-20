"""Web Mercator helpers."""
import math

R = 6378137.0
ORIGIN = math.pi * R

def lonlat_to_3857(lon, lat):
    return math.radians(lon) * R, math.log(math.tan(math.pi / 4 + math.radians(lat) / 2)) * R

def res_at_zoom(zoom, scale=1.0):
    """Web Mercator metres per pixel."""
    return 2 * ORIGIN / (256 * 2 ** zoom) / scale

def scale_denominator(zoom, scale=1.0):
    """Mapnik scale denominator for a zoom (0.28 mm standard pixel)."""
    return res_at_zoom(zoom, scale) / 0.00028
