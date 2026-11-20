#!/usr/bin/env python3
"""Render an area with openstreetmap-carto to a georeferenced GeoTIFF (EPSG:3857).

The bounding box is snapped outward to the web-map pixel grid for the zoom, so at
scale 1 pixels line up with tile.openstreetmap.org. --scale s renders the same area
s times denser (crisp upscaling, e.g. 2 = "@2x").
"""
import argparse, os, sys
sys.path.insert(0, os.path.dirname(__file__))
from geo import AREAS, res_at_zoom
from renderlib import bbox_lonlat_to_3857, snap_bbox, render_array, write_geotiff

ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
g = ap.add_mutually_exclusive_group(required=True)
g.add_argument("--area", choices=AREAS, help="named study area from geo.py")
g.add_argument("--bbox", nargs=4, type=float, metavar=("MINLON", "MINLAT", "MAXLON", "MAXLAT"))
g.add_argument("--bbox3857", nargs=4, type=float, metavar=("MINX", "MINY", "MAXX", "MAXY"))
ap.add_argument("--zoom", type=int, default=17)
ap.add_argument("--scale", type=float, default=1.0)
ap.add_argument("--out", required=True)
a = ap.parse_args()

bb = a.bbox3857 or bbox_lonlat_to_3857(AREAS[a.area] if a.area else a.bbox)
bb = snap_bbox(*bb, a.zoom)
arr = render_array(bb, a.zoom, a.scale)
write_geotiff(arr, bb, a.out, {"zoom": a.zoom, "scale": a.scale, "style": "openstreetmap-carto",
                               "style_version": os.environ.get("CARTO_VERSION", "")})
print(f"{a.out}: {arr.shape[1]}x{arr.shape[0]} px, {res_at_zoom(a.zoom, a.scale):.4f} m/px")
