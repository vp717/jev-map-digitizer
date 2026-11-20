"""Stage `exp-multiimage`: does putting several images in one Jev call hurt quality, and what does it save?

A. Screening: for N tiles (the demo tile + N-1 random 640 px tiles, seeded), compare
   - single: 25 calls per tile, one legend excerpt each (the current method), against
   - batch:  1 call per tile with all 25 legend excerpts and 25 Noul questions.
   Truth = whether the class has a render-diff icon in the tile.
B. Choice check: for each detection of the demo-tile run, crop 40 px around it (x8) and ask
   a Choice over all legend excerpts + "none of these". Keep the detection only if the choice
   is its own class. Compare precision/recall before and after.
Latency is the per-call latency recorded in the API cache when the call was first made.
"""
import csv, io, json, os

def add_args(p):
    p.add_argument("--map", required=True)
    p.add_argument("--gt", required=True)
    p.add_argument("--symbols", required=True)
    p.add_argument("--demo-report", required=True)
    p.add_argument("--tiles", type=int, default=8)
    p.add_argument("--seed", type=int, default=17)
    p.add_argument("--cache", default="cache/api")
    p.add_argument("--api-mode", default="online", choices=["online", "offline", "refresh"])
    p.add_argument("--outdir", required=True)

def run(a):
    import numpy as np, pyogrio, rasterio
    from PIL import Image
    from rasterio.windows import Window
    from mapdig.apicache import ApiCache
    from mapdig.jev import Jev, PRICE_IN
    from mapdig.manifest import Manifest

    m_ = Manifest("exp-multiimage", {k: v for k, v in vars(a).items() if k != "stage"},
                  inputs=[a.map, a.gt, a.symbols, a.demo_report])
    os.makedirs(a.outdir, exist_ok=True)
    def png(im):
        b = io.BytesIO(); im.save(b, "PNG"); return b.getvalue()
    src = rasterio.open(a.map); W, H, T = src.width, src.height, 640
    _, _, _, f = pyogrio.raw.read(a.gt, layer="gt", columns=["label", "px_x", "px_y"], read_geometry=False)
    glab, gx, gy = f[0].astype(str), f[1], f[2]
    sym = json.load(open(a.symbols)); sdir = os.path.dirname(a.symbols)
    entries = [e for e in sym["entries"] if e["crop"]]
    demo = json.load(open(a.demo_report))
    land = (242, 239, 233)
    def legend(e, k):
        icon = Image.open(os.path.join(sdir, e["crop"])).convert("RGB")
        icon = icon.resize((icon.width * k, icon.height * k), Image.LANCZOS)
        side = max(280, icon.width + 8, icon.height + 8)
        c = Image.new("RGB", (side, side), land); c.paste(icon, ((side - icon.width) // 2, (side - icon.height) // 2))
        return png(c)
    cache = ApiCache(a.cache, a.api_mode); jev = Jev(cache)

    # ---- A. screening: single vs batch ----
    rng = np.random.default_rng(a.seed)
    tiles = [(demo["tile"]["x"], demo["tile"]["y"])]
    while len(tiles) < a.tiles:
        x, y = int(rng.integers(0, W - T)), int(rng.integers(0, H - T))
        if all(abs(x - u) >= T or abs(y - v) >= T for u, v in tiles):   # no overlap between tiles
            tiles.append((x, y))
    leg2 = [(e["label"], legend(e, 2)) for e in entries]
    rows, cost = [], {"single": {"calls": 0, "tokens": 0, "latency_s": 0.0}, "batch": {"calls": 0, "tokens": 0, "latency_s": 0.0}}
    for ti, (x, y) in enumerate(tiles):
        rgb = np.moveaxis(src.read((1, 2, 3), window=Window(x, y, T, T)), 0, -1)
        tile_png = png(Image.fromarray(rgb).resize((T * 2, T * 2), Image.LANCZOS))
        b = jev.present_batch(tile_png, leg2)
        cost["batch"]["calls"] += 1; cost["batch"]["tokens"] += b["usage"]["input_tokens"]; cost["batch"]["latency_s"] += b["latency_s"]
        for i, (e, (lab, lpng)) in enumerate(zip(entries, leg2)):
            s1 = jev.present(tile_png, lpng, lab)
            cost["single"]["calls"] += 1; cost["single"]["tokens"] += s1["usage"]["input_tokens"]; cost["single"]["latency_s"] += s1["latency_s"]
            inn = (glab == e["gt_label"]) & (gx >= x) & (gx < x + T) & (gy >= y) & (gy < y + T)
            rows.append({"tile": ti, "x": x, "y": y, "label": lab, "n_true": int(inn.sum()),
                         "p_single": s1["response"]["answers"]["present"]["noul"],
                         "p_batch": b["response"]["answers"][f"q{i:02d}"]["noul"]})
        print(f"tile {ti} ({x},{y}): batch tokens {b['usage']['input_tokens']}, {b['latency_s']}s", flush=True)
    with open(os.path.join(a.outdir, "screening.csv"), "w", newline="") as fh:
        w = csv.DictWriter(fh, list(rows[0])); w.writeheader(); w.writerows(rows)

    def scores(key):
        y_ = np.array([r["n_true"] > 0 for r in rows]); p = np.array([r[key] for r in rows]); hat = p >= 0.5
        pos, neg = p[y_], p[~y_]
        auc = float(np.mean([pp > nn for pp in pos for nn in neg]) + 0.5 * np.mean([pp == nn for pp in pos for nn in neg]))
        return {"accuracy": round(float((hat == y_).mean()), 3), "missed_present": int((y_ & ~hat).sum()),
                "false_present": int((~y_ & hat).sum()), "n_present": int(y_.sum()), "n_absent": int((~y_).sum()),
                "auc": round(auc, 3), "mean_p_present": round(float(pos.mean()), 3), "mean_p_absent": round(float(neg.mean()), 3)}
    ps, pb = np.array([r["p_single"] for r in rows]), np.array([r["p_batch"] for r in rows])
    screening = {"tiles": len(tiles), "pairs": len(rows), "single": scores("p_single"), "batch": scores("p_batch"),
                 "agreement_at_0.5": round(float(((ps >= 0.5) == (pb >= 0.5)).mean()), 3),
                 "corr": round(float(np.corrcoef(ps, pb)[0, 1]), 3), "mean_abs_diff": round(float(np.abs(ps - pb).mean()), 3),
                 "cost": {k: {**v, "usd": round(v["tokens"] * PRICE_IN, 4), "latency_s": round(v["latency_s"], 1)} for k, v in cost.items()}}

    # ---- B. Choice check on the demo tile's detections ----
    tx, ty = demo["tile"]["x"], demo["tile"]["y"]
    tile = np.moveaxis(src.read((1, 2, 3), window=Window(tx - 40, ty - 40, T + 80, T + 80), boundless=True), 0, -1)
    leg8 = [(e["label"], legend(e, 8)) for e in entries]
    crows, ccost = [], {"calls": 0, "tokens": 0, "latency_s": 0.0}
    for pr in demo["predictions"]:
        cx, cy = int(round(pr["x"])) + 40, int(round(pr["y"])) + 40
        crop = png(Image.fromarray(tile[cy - 20:cy + 20, cx - 20:cx + 20]).resize((320, 320), Image.LANCZOS))
        c = jev.which_symbol(crop, leg8)
        ccost["calls"] += 1; ccost["tokens"] += c["usage"]["input_tokens"]; ccost["latency_s"] += c["latency_s"]
        ans = c["response"]["answers"]["which"]
        probs = ans.get("probabilities") or {}
        crows.append({"label": pr["label"], "match": pr["match"], "choice": ans["choice"], "conf": ans.get("confidence"),
                      "p_own": probs.get(pr["label"]), "p_none": probs.get("none of these"),
                      "keep": ans["choice"] == pr["label"]})
    with open(os.path.join(a.outdir, "choice.csv"), "w", newline="") as fh:
        w = csv.DictWriter(fh, list(crows[0])); w.writeheader(); w.writerows(crows)
    n_truth = demo["metrics"]["tp"] + demo["metrics"]["fn"]
    def prf(rs):
        tp = sum(r["match"] == "TP" for r in rs); P = tp / len(rs) if rs else 0; R = tp / n_truth
        return {"pred": len(rs), "tp": tp, "precision": round(P, 3), "recall": round(R, 3), "f1": round(2 * P * R / (P + R), 3) if P + R else 0}
    kept = [r for r in crows if r["keep"]]
    choice = {"before": prf(crows), "after": prf(kept),
              "fp_removed": sum(r["match"] == "FP" and not r["keep"] for r in crows),
              "fp_total": sum(r["match"] == "FP" for r in crows),
              "tp_lost": sum(r["match"] == "TP" and not r["keep"] for r in crows),
              "cost": {**ccost, "usd": round(ccost["tokens"] * PRICE_IN, 4), "latency_s": round(ccost["latency_s"], 1)}}
    out = {"screening": screening, "choice": choice, "api_new_calls": cache.calls, "api_cache_hits": cache.hits}
    json.dump(out, open(os.path.join(a.outdir, "summary.json"), "w"), indent=1)
    m_.extra.update(out); m_.write(os.path.join(a.outdir, "manifest.json"), outputs=["screening.csv", "choice.csv", "summary.json"])
    print(json.dumps(out, indent=1))
