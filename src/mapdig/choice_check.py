"""Stage `choice-check`: assign / verify each detection's class with one Jev Choice among ALL legend rows.

Crop = Jev's loop box + margin, x8, padded to 280 px with the land colour (change 3). Options =
every legend row's excerpt (variant rows included) + "none of these". A pick counts for the
row's class. Rules: strict = keep only if the picked row's class is the detection's class;
gentle = drop only if a row of a *different* class was picked. Predictions are re-matched to
the ground truth after filtering, and recall is also reported per drawn appearance.
"""
import collections, io, json, os

LAND = (242, 239, 233)

def add_args(p):
    p.add_argument("--map", required=True)
    p.add_argument("--symbols", required=True)
    p.add_argument("--demo-report", required=True)
    p.add_argument("--label-mode", choices=["names", "codes"], default="names")
    p.add_argument("--only-classes", nargs="*", default=[], help="score only these classes (truth and detections)")
    p.add_argument("--margin", type=int, default=3)
    p.add_argument("--match-px", type=float, default=7)
    p.add_argument("--cache", default="cache/api")
    p.add_argument("--api-mode", default="online", choices=["online", "offline", "refresh"])
    p.add_argument("--outdir", required=True)

def match(preds, truth, px):
    pairs = sorted((float(((p["x"] - t["x"]) ** 2 + (p["y"] - t["y"]) ** 2) ** 0.5), i, j)
                   for i, p in enumerate(preds) for j, t in enumerate(truth) if p["gt_label"] == t["label"])
    up, ut = set(), set()
    for d, i, j in pairs:
        if d <= px and i not in up and j not in ut:
            up.add(i); ut.add(j)
    tp = len(up); P = tp / len(preds) if preds else 0.0; R = tp / len(truth) if truth else 0.0
    by_app = collections.defaultdict(lambda: [0, 0])
    for j, t in enumerate(truth):
        key = f"{t['label']} | {t.get('appearance') or 'default'}"
        by_app[key][0] += 1; by_app[key][1] += j in ut
    return {"pred": len(preds), "tp": tp, "fp": len(preds) - tp, "fn": len(truth) - tp, "precision": round(P, 3),
            "recall": round(R, 3), "f1": round(2 * P * R / (P + R), 3) if P + R else 0.0,
            "by_appearance": {k: {"n": v[0], "found": v[1]} for k, v in sorted(by_app.items())}}

def run(a):
    import numpy as np, rasterio
    from PIL import Image
    from rasterio.windows import Window
    from mapdig.apicache import ApiCache
    from mapdig.jev import Jev, PRICE_IN
    from mapdig.manifest import Manifest

    m_ = Manifest("choice-check", {k: v for k, v in vars(a).items() if k != "stage"}, inputs=[a.map, a.symbols, a.demo_report])
    os.makedirs(os.path.join(a.outdir, "crops"), exist_ok=True)
    def png(im):
        b = io.BytesIO(); im.save(b, "PNG"); return b.getvalue()
    def pad(im):
        side = max(280, im.width, im.height)
        c = Image.new("RGB", (side, side), LAND); c.paste(im, ((side - im.width) // 2, (side - im.height) // 2)); return c
    sym = json.load(open(a.symbols)); sdir = os.path.dirname(a.symbols)
    entries = [e for e in sym["entries"] if e["crop"]]
    if a.label_mode == "codes":
        from mapdig.labels import anonymize
        entries = anonymize(entries)
    row_class = {e["label"]: e["gt_label"] for e in entries}
    def legend(e):
        icon = Image.open(os.path.join(sdir, e["crop"])).convert("RGB")
        return png(pad(icon.resize((icon.width * 8, icon.height * 8), Image.LANCZOS)))
    opts = [(e["label"], legend(e)) for e in entries]
    r = json.load(open(a.demo_report)); tx, ty = r["tile"]["x"], r["tile"]["y"]
    boxes = {(s["label"], tuple(s["sub"]), s["pass"]): s["box"] for s in r["loop"] if s["action"].startswith("detect")}
    src = rasterio.open(a.map)
    cache = ApiCache(a.cache, a.api_mode); jev = Jev(cache)
    cost = {"calls": 0, "tokens": 0, "latency_s": 0.0}
    rows = []
    for i, pr in enumerate(r["predictions"]):
        b = boxes[(pr["label"], tuple(pr["sub"]), pr["pass_index"])]
        x0, y0 = int(np.floor(tx + b[0])) - a.margin, int(np.floor(ty + b[1])) - a.margin
        x1, y1 = int(np.ceil(tx + b[2])) + a.margin, int(np.ceil(ty + b[3])) + a.margin
        im = Image.fromarray(np.moveaxis(src.read((1, 2, 3), window=Window(x0, y0, x1 - x0, y1 - y0), boundless=True), 0, -1))
        img = pad(im.resize((im.width * 8, im.height * 8), Image.LANCZOS)); img.save(os.path.join(a.outdir, "crops", f"{i:02d}.png"))
        e = jev.which_symbol(png(img), opts)
        cost["calls"] += 1; cost["tokens"] += e["usage"]["input_tokens"]; cost["latency_s"] += e["latency_s"]
        ans = e["response"]["answers"]["which"]; probs = ans.get("probabilities") or {}
        cls = row_class.get(ans["choice"])   # None for "none of these"
        p_class = sum(v for k, v in probs.items() if row_class.get(k) == pr["gt_label"])
        rows.append({**{k: pr[k] for k in ("label", "gt_label", "x", "y", "match")}, "choice": ans["choice"], "choice_class": cls,
                     "p_class": round(p_class, 3), "p_none": probs.get("none of these"),
                     "strict": cls == pr["gt_label"], "gentle": not (cls is not None and cls != pr["gt_label"])})
    truth = [t for t in r["truth"] if not a.only_classes or t["label"] in a.only_classes]
    out = {"loop": match(r["predictions"], truth, a.match_px),
           "strict": match([q for q in rows if q["strict"]], truth, a.match_px),
           "gentle": match([q for q in rows if q["gentle"]], truth, a.match_px),
           "rows": rows, "n_options": len(opts) + 1,
           "cost": {**cost, "usd": round(cost["tokens"] * PRICE_IN, 4), "latency_s": round(cost["latency_s"], 1)},
           "api_new_calls": cache.calls, "api_cache_hits": cache.hits}
    json.dump(out, open(os.path.join(a.outdir, "summary.json"), "w"), indent=1, default=float)
    m_.extra.update({k: out[k] for k in ("cost", "api_new_calls")}); m_.write(os.path.join(a.outdir, "manifest.json"), outputs=["summary.json", "crops/"])
    print(json.dumps({k: {kk: vv for kk, vv in out[k].items() if kk != "by_appearance"} for k in ("loop", "strict", "gentle")} | {"cost": out["cost"]}, indent=1))
