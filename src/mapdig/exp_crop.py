"""Stage `exp-crop`: does a tighter crop make the Choice check (change 2) better?

Same 94 detections, same Choice question and 26 options as exp-multiimage; only the crop
image changes:
  wide (baseline of change 2): 40x40 px around the point, x8 -> 320 px
  box:  Jev's loop box + --margin px, x8, padded to >=280 px with the land colour
  sq20: 20x20 px around the point, x8 -> 160 px, padded to 280 px
Padding mirrors how the legend excerpts (the options) are made, so crop and options show
the icon at the same scale.
"""
import csv, io, json, os

def add_args(p):
    p.add_argument("--map", required=True)
    p.add_argument("--symbols", required=True)
    p.add_argument("--demo-report", required=True)
    p.add_argument("--baseline-choice", required=True, help="exp_multiimage/choice.csv (the 40 px crop)")
    p.add_argument("--margin", type=int, default=3)
    p.add_argument("--cache", default="cache/api")
    p.add_argument("--api-mode", default="online", choices=["online", "offline", "refresh"])
    p.add_argument("--outdir", required=True)

LAND = (242, 239, 233)

def pad(im, side_min=280):
    side = max(side_min, im.width, im.height)
    from PIL import Image
    c = Image.new("RGB", (side, side), LAND); c.paste(im, ((side - im.width) // 2, (side - im.height) // 2)); return c

def run(a):
    import numpy as np, rasterio
    from PIL import Image
    from rasterio.windows import Window
    from mapdig.apicache import ApiCache
    from mapdig.jev import Jev, PRICE_IN
    from mapdig.manifest import Manifest

    m_ = Manifest("exp-crop", {k: v for k, v in vars(a).items() if k != "stage"},
                  inputs=[a.map, a.symbols, a.demo_report, a.baseline_choice])
    os.makedirs(os.path.join(a.outdir, "crops"), exist_ok=True)
    def png(im):
        b = io.BytesIO(); im.save(b, "PNG"); return b.getvalue()
    r = json.load(open(a.demo_report))
    sym = json.load(open(a.symbols)); sdir = os.path.dirname(a.symbols)
    entries = [e for e in sym["entries"] if e["crop"]]
    def legend(e, k=8):
        icon = Image.open(os.path.join(sdir, e["crop"])).convert("RGB")
        return png(pad(icon.resize((icon.width * k, icon.height * k), Image.LANCZOS)))
    opts = [(e["label"], legend(e)) for e in entries]
    labels = {e["label"] for e in entries}
    tx, ty, M = r["tile"]["x"], r["tile"]["y"], 40
    src = rasterio.open(a.map)
    big = np.moveaxis(src.read((1, 2, 3), window=Window(tx - M, ty - M, 640 + 2 * M, 640 + 2 * M), boundless=True), 0, -1)
    boxes = {(s["label"], tuple(s["sub"]), s["pass"]): s["box"] for s in r["loop"] if s["action"].startswith("detect")}
    base = list(csv.DictReader(open(a.baseline_choice)))
    cache = ApiCache(a.cache, a.api_mode); jev = Jev(cache)
    cost = {v: {"calls": 0, "tokens": 0, "latency_s": 0.0} for v in ("box", "sq20")}
    rows = []
    for i, (pr, b0) in enumerate(zip(r["predictions"], base)):
        assert b0["label"] == pr["label"] and b0["match"] == pr["match"]
        bx = boxes[(pr["label"], tuple(pr["sub"]), pr["pass_index"])]
        x0, y0 = int(np.floor(bx[0])) - a.margin + M, int(np.floor(bx[1])) - a.margin + M
        x1, y1 = int(np.ceil(bx[2])) + a.margin + M, int(np.ceil(bx[3])) + a.margin + M
        cx, cy = int(round(pr["x"])) + M, int(round(pr["y"])) + M
        crops = {"box": Image.fromarray(big[y0:y1, x0:x1]),
                 "sq20": Image.fromarray(big[cy - 10:cy + 10, cx - 10:cx + 10])}
        row = {"i": i, "label": pr["label"], "match": pr["match"], "box_px": [x1 - x0, y1 - y0],
               "wide_choice": b0["choice"], "wide_p_own": b0["p_own"], "wide_p_none": b0["p_none"]}
        for v, im in crops.items():
            img = pad(im.resize((im.width * 8, im.height * 8), Image.LANCZOS))
            img.save(os.path.join(a.outdir, "crops", f"{i:02d}_{v}.png"))
            e = jev.which_symbol(png(img), opts)
            c = cost[v]; c["calls"] += 1; c["tokens"] += e["usage"]["input_tokens"]; c["latency_s"] += e["latency_s"]
            ans = e["response"]["answers"]["which"]; pr_ = ans.get("probabilities") or {}
            row[f"{v}_choice"] = ans["choice"]; row[f"{v}_p_own"] = pr_.get(pr["label"]); row[f"{v}_p_none"] = pr_.get("none of these")
        rows.append(row)
    n_truth = r["metrics"]["tp"] + r["metrics"]["fn"]
    def prf(keep):
        rs = [q for q in rows if keep(q)]; tp = sum(q["match"] == "TP" for q in rs)
        P = tp / len(rs) if rs else 0; R = tp / n_truth
        return {"pred": len(rs), "tp": tp, "fp": len(rs) - tp, "precision": round(P, 3), "recall": round(R, 3),
                "f1": round(2 * P * R / (P + R), 3) if P + R else 0}
    res = {"before": prf(lambda q: True)}
    for v in ("wide", "box", "sq20"):
        strict = lambda q, v=v: q[f"{v}_choice"] == q["label"]
        gentle = lambda q, v=v: not (q[f"{v}_choice"] in labels and q[f"{v}_choice"] != q["label"])
        res[v] = {"strict": prf(strict), "gentle": prf(gentle),
                  "fp_removed_strict": sum(q["match"] == "FP" and not strict(q) for q in rows),
                  "tp_lost_strict": sum(q["match"] == "TP" and not strict(q) for q in rows),
                  "fp_removed_gentle": sum(q["match"] == "FP" and not gentle(q) for q in rows),
                  "tp_lost_gentle": sum(q["match"] == "TP" and not gentle(q) for q in rows),
                  "choice_none": sum(q[f"{v}_choice"] == "none of these" for q in rows)}
    res["cost"] = {v: {**c, "usd": round(c["tokens"] * PRICE_IN, 4), "latency_s": round(c["latency_s"], 1)} for v, c in cost.items()}
    res["median_box_px"] = [float(np.median([q["box_px"][0] for q in rows])), float(np.median([q["box_px"][1] for q in rows]))]
    res["api_new_calls"], res["api_cache_hits"] = cache.calls, cache.hits
    with open(os.path.join(a.outdir, "choices.csv"), "w", newline="") as fh:
        w = csv.DictWriter(fh, list(rows[0])); w.writeheader(); w.writerows(rows)
    json.dump(res, open(os.path.join(a.outdir, "summary.json"), "w"), indent=1)
    m_.extra.update(res); m_.write(os.path.join(a.outdir, "manifest.json"), outputs=["choices.csv", "summary.json", "crops/"])
    print(json.dumps(res, indent=1))
