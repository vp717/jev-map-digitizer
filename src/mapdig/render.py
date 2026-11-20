"""Stage `render`: an area to a georeferenced GeoTIFF (EPSG:3857), snapped to the web-map pixel grid."""
import os

def add_args(p):
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument("--bbox", nargs=4, type=float, metavar=("MINLON", "MINLAT", "MAXLON", "MAXLAT"))
    g.add_argument("--bbox3857", nargs=4, type=float, metavar=("MINX", "MINY", "MAXX", "MAXY"))
    p.add_argument("--zoom", type=int, default=17)
    p.add_argument("--scale", type=float, default=1.0, help="Mapnik scale factor (crisp upscaling)")
    p.add_argument("--out", required=True)

def run(a):
    from mapdig.geo import res_at_zoom
    from mapdig.renderlib import bbox_lonlat_to_3857, snap_bbox, render_array, write_geotiff
    bb = snap_bbox(*(a.bbox3857 or bbox_lonlat_to_3857(a.bbox)), a.zoom)
    arr = render_array(bb, a.zoom, a.scale)
    write_geotiff(arr, bb, a.out, {"zoom": a.zoom, "scale": a.scale, "style": "openstreetmap-carto",
                                   "style_version": os.environ.get("CARTO_VERSION", "")})
    print(f"{a.out}: {arr.shape[1]}x{arr.shape[0]} px, {res_at_zoom(a.zoom, a.scale):.4f} m/px")
