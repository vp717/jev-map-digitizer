"""Stage `groundtruth`: base render + ground truth by render diff.

Render the area once (this is the evaluation image), then once per class with that class's
MarkersSymbolizers at opacity 0. Opacity 0 still takes part in collision/placement, so
nothing else moves; the changed pixels are exactly where that class was drawn. Each
connected component is one drawn icon; touching icons are split using the legend icon size.
Writes into --outdir: map.tif, gt.gpkg (layer "gt"), gt_summary.csv, manifest.json.
"""
import csv, json, os, time

def add_args(p):
    p.add_argument("--area", required=True, help="area name (recorded only)")
    p.add_argument("--bbox", nargs=4, type=float, required=True, metavar=("MINLON", "MINLAT", "MAXLON", "MAXLAT"))
    p.add_argument("--zoom", type=int, required=True)
    p.add_argument("--scale", type=float, required=True)
    p.add_argument("--classes", required=True)
    p.add_argument("--legend-gt", required=True, help="legend sheet_gt.json for this zoom/scale (icon sizes)")
    p.add_argument("--outdir", required=True)

def run(a):
    import xml.etree.ElementTree as ET
    import numpy as np
    from scipy import ndimage
    from osgeo import ogr, osr
    from mapdig.geo import res_at_zoom
    from mapdig.manifest import Manifest
    from mapdig.renderlib import STYLE_XML, bbox_lonlat_to_3857, snap_bbox, render_array, write_geotiff

    ogr.UseExceptions()
    m_ = Manifest("groundtruth", {"area": a.area, "bbox": a.bbox, "zoom": a.zoom, "scale": a.scale},
                  inputs=[a.classes, a.legend_gt])
    os.makedirs(a.outdir, exist_ok=True)
    rows_ = list(csv.DictReader(open(a.classes)))
    classes, seen_files = [], set()
    for row in rows_:   # one ground-truth class per icon file (variant legend rows share their class)
        if row["file"] not in seen_files:
            seen_files.add(row["file"])
            classes.append({**row, "label": row.get("class_label") or row["label"]})
    icon_size = {}
    for it in json.load(open(a.legend_gt))["items"]:
        icon_size.setdefault(it["file"], (it["box"][2] - it["box"][0], it["box"][3] - it["box"][1]))
    base_xml = open(STYLE_XML).read()
    from mapdig.geo import scale_denominator
    sd = scale_denominator(a.zoom)

    def hide_class_xml(svg_file, appearance=None):
        """Opacity 0 on this file's markers; with `appearance` (fill, opacity) only those drawn that way."""
        root = ET.fromstring(base_xml)
        n = 0
        for ms in root.iter("MarkersSymbolizer"):
            if ms.get("file") == svg_file and (appearance is None or (ms.get("fill"), ms.get("opacity")) == appearance):
                ms.set("opacity", "0"); n += 1
        return ET.tostring(root, encoding="unicode"), n

    def appearances(svg_file):
        """Distinct (fill, opacity) this file is drawn with at the zoom, with the tag rules producing each."""
        root = ET.fromstring(base_xml)
        st = next(x for x in root.findall("Style") if x.get("name") == "amenity-points")
        out = {}
        for ru in st.findall("Rule"):
            ms = ru.find("MarkersSymbolizer")
            if ms is None or ms.get("file") != svg_file:
                continue
            lo = float(ru.findtext("MinScaleDenominator") or 0); hi = float(ru.findtext("MaxScaleDenominator") or 1e30)
            if lo <= sd < hi:
                out.setdefault((ms.get("fill"), ms.get("opacity")), []).append(" ".join((ru.findtext("Filter") or "").split()))
        return out

    bb = snap_bbox(*bbox_lonlat_to_3857(a.bbox), a.zoom)
    res = res_at_zoom(a.zoom, a.scale)
    t0 = time.time()
    base = render_array(bb, a.zoom, a.scale)
    h, w = base.shape[:2]
    write_geotiff(base, bb, os.path.join(a.outdir, "map.tif"), {"zoom": a.zoom, "scale": a.scale, "area": a.area,
                  "style": "openstreetmap-carto", "style_version": os.environ.get("CARTO_VERSION", "")})
    print(f"base {w}x{h} px rendered in {time.time()-t0:.0f}s", flush=True)

    gpkg = os.path.join(a.outdir, "gt.gpkg")
    if os.path.exists(gpkg):
        os.remove(gpkg)
    ds = ogr.GetDriverByName("GPKG").CreateDataSource(gpkg)
    srs = osr.SpatialReference(); srs.ImportFromEPSG(3857)
    lyr = ds.CreateLayer("gt", srs, ogr.wkbPoint)
    for name, typ in [("class", ogr.OFTString), ("label", ogr.OFTString), ("grp", ogr.OFTString),
                      ("px_x", ogr.OFTReal), ("px_y", ogr.OFTReal), ("bbox_w", ogr.OFTInteger),
                      ("bbox_h", ogr.OFTInteger), ("n_px", ogr.OFTInteger), ("suspect", ogr.OFTInteger),
                      ("appearance", ogr.OFTString), ("variant_rules", ogr.OFTString)]:
        lyr.CreateField(ogr.FieldDefn(name, typ))

    summary, struct = [], np.ones((3, 3), bool)
    for c in classes:
        t1 = time.time()
        xml, n_sym = hide_class_xml(c["file"])
        if n_sym == 0:
            raise SystemExit(f"{c['file']}: no MarkersSymbolizer uses this file")
        hidden = render_array(bb, a.zoom, a.scale, xml=xml)
        diff = np.abs(base.astype(np.int16) - hidden.astype(np.int16)).max(axis=2) > 8
        # merge disconnected parts of one icon before labelling
        grown = ndimage.binary_dilation(diff, struct, iterations=max(1, round(2 * a.scale)))
        lab, _ = ndimage.label(grown, struct)
        lab[~diff] = 0
        # which appearance each drawn icon has (only needed when the file is drawn more than one way)
        apps = appearances(c["file"])
        app_masks = {}
        if len(apps) > 1:
            for app in apps:
                xml_a, _ = hide_class_xml(c["file"], app)
                hid_a = render_array(bb, a.zoom, a.scale, xml=xml_a)
                app_masks[app] = np.abs(base.astype(np.int16) - hid_a.astype(np.int16)).max(axis=2) > 8
        def app_of(cx, cy, pw, ph):
            if len(apps) == 1:
                return next(iter(apps))
            y0_, y1_ = int(max(cy - ph / 2, 0)), int(min(cy + ph / 2 + 1, h)); x0_, x1_ = int(max(cx - pw / 2, 0)), int(min(cx + pw / 2 + 1, w))
            scores = {app: int(msk[y0_:y1_, x0_:x1_].sum()) for app, msk in app_masks.items()}
            best = max(scores, key=scores.get)
            return best if scores[best] > 0 else (None, None)
        def app_str(app):
            return "unknown" if app[0] is None else app[0] + (f"@{app[1]}" if app[1] else "")
        iw, ih = icon_size[c["file"]]
        n_drawn = n_split = n_susp = 0
        app_counts = {}
        for i, sl in enumerate(ndimage.find_objects(lab), start=1):
            if sl is None:
                continue
            ys, xs = sl
            bw, bh = xs.stop - xs.start, ys.stop - ys.start
            # touching icons merge; split into as many icon-sized cells as fit (icons never overlap)
            nx, ny = max(1, round(bw / (iw + 1))), max(1, round(bh / (ih + 1)))
            total = (lab[sl] == i).sum()
            parts = []
            for jx in range(nx):
                for jy in range(ny):
                    sub = lab[ys.start + jy * bh // ny: ys.start + (jy + 1) * bh // ny,
                              xs.start + jx * bw // nx: xs.start + (jx + 1) * bw // nx] == i
                    if sub.sum() >= 0.25 * total / (nx * ny):
                        parts.append((xs.start + (jx + 0.5) * bw / nx, ys.start + (jy + 0.5) * bh / ny,
                                      bw / nx, bh / ny, int(sub.sum())))
            susp = int(bw / nx > 1.5 * iw + 2 or bh / ny > 1.5 * ih + 2)   # still not icon-sized: review
            n_split += len(parts) > 1
            n_susp += susp * len(parts)
            for cx, cy, pw, ph, npx in parts:   # pixel-edge coordinates
                app = app_of(cx, cy, pw, ph)
                app_counts[app_str(app)] = app_counts.get(app_str(app), 0) + 1
                f = ogr.Feature(lyr.GetLayerDefn())
                for k, v in [("class", c["file"]), ("label", c["label"]), ("grp", c["group"]), ("px_x", cx),
                             ("px_y", cy), ("bbox_w", round(pw)), ("bbox_h", round(ph)),
                             ("n_px", npx), ("suspect", susp), ("appearance", app_str(app)),
                             ("variant_rules", " | ".join(apps.get(app, [])))]:
                    f.SetField(k, v)
                pt = ogr.Geometry(ogr.wkbPoint); pt.AddPoint_2D(bb[0] + cx * res, bb[3] - cy * res)
                f.SetGeometry(pt); lyr.CreateFeature(f)
                n_drawn += 1
        summary.append((c["label"], n_drawn, n_split, n_susp, json.dumps(app_counts, sort_keys=True)))
        print(f"{c['label']:<20} {n_drawn:5d} drawn  {n_split:3d} split  {n_susp:3d} suspect  {app_counts if len(apps) > 1 else ''}  ({time.time()-t1:.0f}s)",
              flush=True)
    ds = None
    with open(os.path.join(a.outdir, "gt_summary.csv"), "w", newline="") as fh:
        wr = csv.writer(fh); wr.writerow(["label", "drawn", "merged_split", "suspect", "appearances"]); wr.writerows(summary)
    m_.extra["size_px"] = [w, h]
    m_.extra["icons_total"] = sum(s[1] for s in summary)
    m_.write(os.path.join(a.outdir, "manifest.json"), outputs=["map.tif", "gt.gpkg", "gt_summary.csv"])
    print(f"wrote {gpkg}; {m_.extra['icons_total']} icons in {time.time()-t0:.0f}s")
