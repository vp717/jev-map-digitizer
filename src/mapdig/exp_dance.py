"""Stage `exp-dance` (change 4): can Jev tell Fitness from Dance when it is given the choice?

A. Choice check on the tile's detections (loop run with Dance included and forced), using
   the tight crop from change 3 (Jev's box + 3 px, x8, padded) and 26 options incl. Dance.
B. Every Fitness and Dance icon in the area's ground truth, cropped from its true box
   (+3 px, x8, padded), asked twice: a Choice over all 26 legend options + "none", and a
   two-way Choice {Fitness, Dance, none}. Gives a fitness/dance confusion table.
"""
import csv, io, json, os

LAND = (242, 239, 233)

def add_args(p):
    p.add_argument("--map", required=True)
    p.add_argument("--gt", required=True)
    p.add_argument("--symbols", required=True)
    p.add_argument("--demo-report", required=True)
    p.add_argument("--margin", type=int, default=3)
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

    m_ = Manifest("exp-dance", {k: v for k, v in vars(a).items() if k != "stage"}, inputs=[a.map, a.gt, a.symbols, a.demo_report])
    os.makedirs(os.path.join(a.outdir, "crops"), exist_ok=True)
    def png(im):
        b = io.BytesIO(); im.save(b, "PNG"); return b.getvalue()
    def pad(im):
        side = max(280, im.width, im.height)
        c = Image.new("RGB", (side, side), LAND); c.paste(im, ((side - im.width) // 2, (side - im.height) // 2)); return c
    sym = json.load(open(a.symbols)); sdir = os.path.dirname(a.symbols)
    entries = [e for e in sym["entries"] if e["crop"]]
    def legend(e):
        icon = Image.open(os.path.join(sdir, e["crop"])).convert("RGB")
        return png(pad(icon.resize((icon.width * 8, icon.height * 8), Image.LANCZOS)))
    opts = [(e["label"], legend(e)) for e in entries]
    two = [o for o in opts if o[0] in ("Fitness station", "Dance")]
    labels = {e["label"] for e in entries}
    src = rasterio.open(a.map)
    cache = ApiCache(a.cache, a.api_mode); jev = Jev(cache)
    cost = {"calls": 0, "tokens": 0, "latency_s": 0.0}
    def ask(crop_img, options):
        e = jev.which_symbol(png(crop_img), options)
        cost["calls"] += 1; cost["tokens"] += e["usage"]["input_tokens"]; cost["latency_s"] += e["latency_s"]
        ans = e["response"]["answers"]["which"]
        return ans["choice"], ans.get("probabilities") or {}
    def crop_xyxy(x0, y0, x1, y1):
        x0, y0 = int(np.floor(x0)) - a.margin, int(np.floor(y0)) - a.margin
        x1, y1 = int(np.ceil(x1)) + a.margin, int(np.ceil(y1)) + a.margin
        rgb = np.moveaxis(src.read((1, 2, 3), window=Window(x0, y0, x1 - x0, y1 - y0), boundless=True), 0, -1)
        im = Image.fromarray(rgb); return pad(im.resize((im.width * 8, im.height * 8), Image.LANCZOS))

    # ---- A: Choice check on the tile's detections ----
    r = json.load(open(a.demo_report)); tx, ty = r["tile"]["x"], r["tile"]["y"]
    boxes = {(s["label"], tuple(s["sub"]), s["pass"]): s["box"] for s in r["loop"] if s["action"].startswith("detect")}
    rows = []
    for i, pr in enumerate(r["predictions"]):
        b = boxes[(pr["label"], tuple(pr["sub"]), pr["pass_index"])]
        img = crop_xyxy(tx + b[0], ty + b[1], tx + b[2], ty + b[3])
        if pr["label"] in ("Fitness station", "Dance"):
            img.save(os.path.join(a.outdir, "crops", f"det_{i:02d}.png"))
        ch, pb = ask(img, opts)
        rows.append({"i": i, "label": pr["label"], "match": pr["match"], "choice": ch, "p_own": pb.get(pr["label"]),
                     "p_fitness": pb.get("Fitness station"), "p_dance": pb.get("Dance"), "x": pr["x"], "y": pr["y"]})
    n_truth = r["metrics"]["tp"] + r["metrics"]["fn"]
    def prf(rs):
        tp = sum(q["match"] == "TP" for q in rs); P = tp / len(rs) if rs else 0; R = tp / n_truth
        return {"pred": len(rs), "tp": tp, "fp": len(rs) - tp, "precision": round(P, 3), "recall": round(R, 3),
                "f1": round(2 * P * R / (P + R), 3) if P + R else 0}
    A = {"loop": prf(rows), "strict": prf([q for q in rows if q["choice"] == q["label"]]),
         "gentle": prf([q for q in rows if not (q["choice"] in labels and q["choice"] != q["label"])]),
         "per_class": r["metrics"]["per_class"],
         "fd_detections": [q for q in rows if q["label"] in ("Fitness station", "Dance")]}

    # ---- B: every Fitness / Dance icon in the area's ground truth ----
    _, _, _, f = pyogrio.raw.read(a.gt, layer="gt", columns=["label", "px_x", "px_y", "bbox_w", "bbox_h"], read_geometry=False)
    lab, gx, gy, bw, bh = f[0].astype(str), f[1], f[2], f[3], f[4]
    icons = []
    for k in np.flatnonzero(np.isin(lab, ["Fitness station", "Dance"])):
        img = crop_xyxy(gx[k] - bw[k] / 2, gy[k] - bh[k] / 2, gx[k] + bw[k] / 2, gy[k] + bh[k] / 2)
        img.save(os.path.join(a.outdir, "crops", f"gt_{k:04d}.png"))
        c26, p26 = ask(img, opts); c2, p2 = ask(img, two)
        icons.append({"k": int(k), "truth": lab[k], "x": float(gx[k]), "y": float(gy[k]), "choice26": c26,
                      "p26_fitness": p26.get("Fitness station"), "p26_dance": p26.get("Dance"),
                      "choice2": c2, "p2_fitness": p2.get("Fitness station"), "p2_dance": p2.get("Dance"),
                      "crop": f"crops/gt_{k:04d}.png"})
    def confusion(key):
        out = {}
        for t in ("Fitness station", "Dance"):
            cs = [q[key] for q in icons if q["truth"] == t]
            out[t] = {"n": len(cs), "correct": sum(c == t for c in cs),
                      "as_other": sum(c in ("Fitness station", "Dance") and c != t for c in cs),
                      "as_none": sum(c == "none of these" for c in cs),
                      "as_else": sum(c not in ("Fitness station", "Dance", "none of these") for c in cs),
                      "choices": sorted(set(cs))}
        return out
    B = {"icons": icons, "choice26": confusion("choice26"), "choice2": confusion("choice2")}
    out = {"A": A, "B": B, "cost": {**cost, "usd": round(cost["tokens"] * PRICE_IN, 4), "latency_s": round(cost["latency_s"], 1)},
           "api_new_calls": cache.calls, "api_cache_hits": cache.hits,
           "dance_screening": next(s for s in r["screening"] if s["label"] == "Dance")}
    json.dump(out, open(os.path.join(a.outdir, "summary.json"), "w"), indent=1, default=float)
    m_.extra.update({k: out[k] for k in ("cost", "api_new_calls")})
    m_.write(os.path.join(a.outdir, "manifest.json"), outputs=["summary.json", "crops/"])
    print(json.dumps({"A": {k: A[k] for k in ("loop", "strict", "gentle")}, "B26": B["choice26"], "B2": B["choice2"], "cost": out["cost"]}, indent=1))
