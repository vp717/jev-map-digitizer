"""Stage `pilot-jev`: can Jev locate small legend symbols at all, and at what magnification?

For each (tile_px, k) setup and class: tiles that contain the class (an instance placed at a
random offset) and tiles that don't. One Jev call per tile asks Noul "present?" and Box
"where?". Records whether the box contains a ground-truth instance, the distance from the box
centre to the nearest instance, box size, P(present), tokens. All calls go through the API cache.
"""
import csv, io, json, os

def add_args(p):
    p.add_argument("--map", required=True, help="map.tif")
    p.add_argument("--gt", required=True, help="gt.gpkg")
    p.add_argument("--legend-sheet", required=True)
    p.add_argument("--legend-gt", required=True)
    p.add_argument("--classes", nargs="+", required=True, help="legend labels")
    p.add_argument("--setups", nargs="+", required=True, help="TILEPXxK, e.g. 640x2 320x4")
    p.add_argument("--positives", type=int, default=10)
    p.add_argument("--negatives", type=int, default=5)
    p.add_argument("--seed", type=int, default=17)
    p.add_argument("--cache", default="cache/api")
    p.add_argument("--api-mode", default="online", choices=["online", "offline", "refresh"])
    p.add_argument("--outdir", required=True)

def _png(im):
    b = io.BytesIO(); im.save(b, "PNG"); return b.getvalue()

def run(a):
    import numpy as np, pyogrio, rasterio
    from PIL import Image
    from rasterio.windows import Window
    from mapdig.apicache import ApiCache
    from mapdig.jev import Jev
    from mapdig.manifest import Manifest

    m_ = Manifest("pilot-jev", {k: v for k, v in vars(a).items() if k not in ("stage",)},
                  inputs=[a.map, a.gt, a.legend_sheet, a.legend_gt])
    os.makedirs(a.outdir, exist_ok=True)
    rng = np.random.default_rng(a.seed)
    src = rasterio.open(a.map)
    W, H = src.width, src.height
    _, _, _, f = pyogrio.raw.read(a.gt, layer="gt", columns=["label", "px_x", "px_y"], read_geometry=False)
    lab, gx, gy = f[0].astype(str), f[1], f[2]
    sheet = Image.open(a.legend_sheet).convert("RGB")
    items = {it["label"]: it for it in json.load(open(a.legend_gt))["items"]}
    land = sheet.getpixel((2, 2))
    cache = ApiCache(a.cache, a.api_mode)
    jev = Jev(cache)

    def legend_png(label, k):
        icon = sheet.crop(tuple(items[label]["box"]))
        icon = icon.resize((icon.width * k, icon.height * k), Image.LANCZOS)
        side = max(280, icon.width + 8, icon.height + 8)
        canvas = Image.new("RGB", (side, side), land)
        canvas.paste(icon, ((side - icon.width) // 2, (side - icon.height) // 2))
        return _png(canvas)

    def tile_png(x, y, s, k):
        rgb = np.moveaxis(src.read((1, 2, 3), window=Window(x, y, s, s)), 0, -1)
        return _png(Image.fromarray(rgb).resize((s * k, s * k), Image.LANCZOS))

    rows = []
    for setup in a.setups:
        s, k = map(int, setup.split("x"))
        if not 280 <= s * k <= 1568:
            raise SystemExit(f"{setup}: {s * k}px is outside Jev's 280-1568 px")
        for label in a.classes:
            cls = lab == label
            idx = rng.choice(np.flatnonzero(cls), size=min(a.positives, cls.sum()), replace=False)
            windows = []
            for i in idx:   # put this instance at a random offset inside the tile (fully inside)
                ox, oy = rng.integers(8, s - 8, size=2)
                windows.append((int(np.clip(gx[i] - ox, 0, W - s)), int(np.clip(gy[i] - oy, 0, H - s))))
            tries = 0
            while len(windows) < len(idx) + a.negatives and tries < 1000:
                tries += 1
                x, y = int(rng.integers(0, W - s)), int(rng.integers(0, H - s))
                if not (cls & (gx >= x - 8) & (gx < x + s + 8) & (gy >= y - 8) & (gy < y + s + 8)).any():
                    windows.append((x, y))
            leg = legend_png(label, k)
            for x, y in windows:
                inside = cls & (gx >= x) & (gx < x + s) & (gy >= y) & (gy < y + s)
                e = jev.present_and_where(tile_png(x, y, s, k), leg, label)
                ans = e["response"]["answers"]
                b = ans["where"]["box"]
                bx0, bx1 = x + b["left"] * s, x + b["right"] * s
                by0, by1 = y + b["top"] * s, y + b["bottom"] * s
                cx, cy = (bx0 + bx1) / 2, (by0 + by1) / 2
                n = int(inside.sum())
                hit = bool((inside & (gx >= bx0) & (gx <= bx1) & (gy >= by0) & (gy <= by1)).any())
                dist = float(np.hypot(gx[inside] - cx, gy[inside] - cy).min()) if n else None
                rows.append({"setup": setup, "tile_px": s, "k": k, "label": label, "x": x, "y": y, "n_true": n,
                             "p_present": ans["present"]["noul"], "box_conf": ans["where"]["confidence"],
                             "box_w_px": round(bx1 - bx0, 1), "box_h_px": round(by1 - by0, 1),
                             "box_hit": hit, "centre_dist_px": None if dist is None else round(dist, 1),
                             "input_tokens": e["usage"].get("input_tokens"), "cache_key": e["key"]})
            print(f"{setup:>6} {label:<10} done ({cache.calls} new calls, {cache.hits} cache hits)", flush=True)

    with open(os.path.join(a.outdir, "calls.csv"), "w", newline="") as fh:
        w = csv.DictWriter(fh, list(rows[0])); w.writeheader(); w.writerows(rows)
    summ = []
    for setup in a.setups:
        for label in a.classes:
            r = [x for x in rows if x["setup"] == setup and x["label"] == label]
            pos, neg = [x for x in r if x["n_true"]], [x for x in r if not x["n_true"]]
            auc = (np.mean([p["p_present"] > q["p_present"] for p in pos for q in neg]) if pos and neg else None)
            summ.append({"setup": setup, "label": label, "pos": len(pos), "neg": len(neg),
                         "p_present_pos": round(float(np.mean([x["p_present"] for x in pos])), 2),
                         "p_present_neg": round(float(np.mean([x["p_present"] for x in neg])), 2) if neg else None,
                         "present_auc": None if auc is None else round(float(auc), 2),
                         "box_hit_rate": round(float(np.mean([x["box_hit"] for x in pos])), 2),
                         "within_7px": round(float(np.mean([x["centre_dist_px"] <= 7 for x in pos])), 2),
                         "median_dist_px": round(float(np.median([x["centre_dist_px"] for x in pos])), 1),
                         "median_box_w_px": round(float(np.median([x["box_w_px"] for x in pos])), 1),
                         "mean_tokens": round(float(np.mean([x["input_tokens"] for x in r])))})
    with open(os.path.join(a.outdir, "summary.csv"), "w", newline="") as fh:
        w = csv.DictWriter(fh, list(summ[0])); w.writeheader(); w.writerows(summ)
    m_.extra.update({"api_new_calls": cache.calls, "api_cache_hits": cache.hits,
                     "input_tokens": sum(x["input_tokens"] or 0 for x in rows)})
    m_.write(os.path.join(a.outdir, "manifest.json"), outputs=["calls.csv", "summary.csv"])
    for s_ in summ:
        print(s_)
