"""Stage `exp-anon` (change 6): do legend NAMES help or hurt Jev, compared with arbitrary codes?

Medical classes only. Tiles: non-overlapping 640 px tiles of the area with >= 1 medical
icon; every tile with a Hospital is taken, then the tiles with the most medical icons, up to
--tiles. For each tile and each label mode (names | codes): demo-tile restricted to the
medical classes (screening -> search loop), then choice-check over ALL legend rows.
Plus: every medical icon in the area, cropped from its true box, asked the all-rows Choice
in both modes (a clean test of the class decision alone).
"""
import argparse, collections, io, json, os

MED = ["Doctor / clinic", "Pharmacy", "Hospital"]
LAND = (242, 239, 233)

def add_args(p):
    p.add_argument("--map", required=True)
    p.add_argument("--gt", required=True)
    p.add_argument("--symbols", required=True)
    p.add_argument("--tiles", type=int, default=8)
    p.add_argument("--cache", default="cache/api")
    p.add_argument("--api-mode", default="online", choices=["online", "offline", "refresh"])
    p.add_argument("--outdir", required=True)

def _run(mod, argv):
    p = argparse.ArgumentParser(); mod.add_args(p); mod.run(p.parse_args(argv))

def run(a):
    import numpy as np, pyogrio, rasterio
    from PIL import Image
    from rasterio.windows import Window
    from mapdig import demo, choice_check
    from mapdig.apicache import ApiCache
    from mapdig.jev import Jev, PRICE_IN
    from mapdig.labels import anonymize
    from mapdig.manifest import Manifest

    m_ = Manifest("exp-anon", {k: v for k, v in vars(a).items() if k != "stage"}, inputs=[a.map, a.gt, a.symbols])
    os.makedirs(a.outdir, exist_ok=True)
    src = rasterio.open(a.map); W, H, T = src.width, src.height, 640
    _, _, _, f = pyogrio.raw.read(a.gt, layer="gt", columns=["label", "px_x", "px_y", "bbox_w", "bbox_h"], read_geometry=False)
    lab, gx, gy, bw, bh = f[0].astype(str), f[1], f[2], f[3], f[4]
    med = np.isin(lab, MED)

    # ---- tile selection ----
    cand = []
    for y in range(0, H - T + 1, T):
        for x in range(0, W - T + 1, T):
            inn = med & (gx >= x) & (gx < x + T) & (gy >= y) & (gy < y + T)
            if inn.any():
                cand.append({"x": x, "y": y, "counts": {c: int((inn & (lab == c)).sum()) for c in MED}})
    hosp = [t for t in cand if t["counts"]["Hospital"]]
    rest = sorted([t for t in cand if not t["counts"]["Hospital"]], key=lambda t: -sum(t["counts"].values()))
    tiles = (hosp + rest)[:a.tiles]
    api = ["--cache", a.cache, "--api-mode", a.api_mode]
    per = collections.defaultdict(list)
    for mode in ("names", "codes"):
        for i, t in enumerate(tiles):
            d = os.path.join(a.outdir, mode, f"t{i}")
            _run(demo, ["--map", a.map, "--gt", a.gt, "--symbols", a.symbols, "--tile", str(t["x"]), str(t["y"]),
                        "--label-mode", mode, "--only-classes", *MED, "--outdir", d] + api)
            _run(choice_check, ["--map", a.map, "--symbols", a.symbols, "--demo-report", os.path.join(d, "report.json"),
                                "--label-mode", mode, "--only-classes", *MED, "--outdir", os.path.join(d, "choice")] + api)
            r = json.load(open(os.path.join(d, "report.json"))); c = json.load(open(os.path.join(d, "choice", "summary.json")))
            per[mode].append({"tile": i, "screening": [{k: s[k] for k in ("label", "gt_label", "p_present", "n_true", "screened_in")} for s in r["screening"]],
                              "loop": {k: c["loop"][k] for k in ("tp", "fp", "fn")}, "strict": {k: c["strict"][k] for k in ("tp", "fp", "fn")},
                              "gentle": {k: c["gentle"][k] for k in ("tp", "fp", "fn")},
                              "per_class_loop": {k: v for k, v in r["metrics"]["per_class"].items() if k in MED},
                              "choices": [{k: q[k] for k in ("gt_label", "match", "choice", "choice_class", "p_class", "p_none")} for q in c["rows"]],
                              "cost": {"loop_usd": r["cost"]["jev_usd"], "loop_calls": r["cost"]["jev_calls"], "choice_usd": c["cost"]["usd"],
                                       "new_calls": r["cost"]["api_new_calls"] + c["api_new_calls"]}})

    def agg(mode, key):
        tp = sum(x[key]["tp"] for x in per[mode]); fp = sum(x[key]["fp"] for x in per[mode]); fn = sum(x[key]["fn"] for x in per[mode])
        P = tp / (tp + fp) if tp + fp else 0; R = tp / (tp + fn) if tp + fn else 0
        return {"tp": tp, "fp": fp, "fn": fn, "precision": round(P, 3), "recall": round(R, 3), "f1": round(2 * P * R / (P + R), 3) if P + R else 0}
    def screen(mode):
        rows = [s for x in per[mode] for s in x["screening"]]
        return {"pairs": len(rows), "correct": sum((s["p_present"] >= 0.5) == (s["n_true"] > 0) for s in rows),
                "missed_present": sum(s["n_true"] > 0 and s["p_present"] < 0.5 for s in rows),
                "false_present": sum(s["n_true"] == 0 and s["p_present"] >= 0.5 for s in rows),
                "by_class": {c: [round(s["p_present"], 2) for s in rows if s["gt_label"] == c] for c in MED},
                "truth_by_class": {c: [s["n_true"] for s in rows if s["gt_label"] == c] for c in MED}}

    # ---- every medical icon in the area: the class decision alone ----
    sym = json.load(open(a.symbols)); sdir = os.path.dirname(a.symbols)
    ents = [e for e in sym["entries"] if e["crop"]]
    def png(im):
        b = io.BytesIO(); im.save(b, "PNG"); return b.getvalue()
    def pad(im):
        side = max(280, im.width, im.height); c = Image.new("RGB", (side, side), LAND); c.paste(im, ((side - im.width) // 2, (side - im.height) // 2)); return c
    def legend(e):
        ic = Image.open(os.path.join(sdir, e["crop"])).convert("RGB"); return png(pad(ic.resize((ic.width * 8, ic.height * 8), Image.LANCZOS)))
    cache = ApiCache(a.cache, a.api_mode); jev = Jev(cache)
    icons = {}; cost = {"calls": 0, "tokens": 0}
    os.makedirs(os.path.join(a.outdir, "icons"), exist_ok=True)
    for mode in ("names", "codes"):
        es = anonymize(ents) if mode == "codes" else ents
        opts = [(e["label"], legend(e)) for e in es]; row_class = {e["label"]: e["gt_label"] for e in es}
        res = []
        for k in np.flatnonzero(med):
            x0, y0 = int(np.floor(gx[k] - bw[k] / 2)) - 3, int(np.floor(gy[k] - bh[k] / 2)) - 3
            x1, y1 = int(np.ceil(gx[k] + bw[k] / 2)) + 3, int(np.ceil(gy[k] + bh[k] / 2)) + 3
            im = Image.fromarray(np.moveaxis(src.read((1, 2, 3), window=Window(x0, y0, x1 - x0, y1 - y0), boundless=True), 0, -1))
            img = pad(im.resize((im.width * 8, im.height * 8), Image.LANCZOS))
            if mode == "names":
                img.save(os.path.join(a.outdir, "icons", f"{k:04d}.png"))
            e = jev.which_symbol(png(img), opts); cost["calls"] += 1; cost["tokens"] += e["usage"]["input_tokens"]
            ans = e["response"]["answers"]["which"]; probs = ans.get("probabilities") or {}
            res.append({"k": int(k), "truth": lab[k], "choice_class": row_class.get(ans["choice"]) or "none",
                        "choice_row": ans["choice"], "p_true": round(sum(v for kk, v in probs.items() if row_class.get(kk) == lab[k]), 3)})
        conf = {t: collections.Counter(q["choice_class"] for q in res if q["truth"] == t) for t in MED}
        icons[mode] = {"n": len(res), "correct": sum(q["choice_class"] == q["truth"] for q in res),
                       "confusion": {t: dict(c) for t, c in conf.items()},
                       "mean_p_true": round(float(np.mean([q["p_true"] for q in res])), 3), "rows": res}
    out = {"tiles": tiles, "per_tile": per,
           "summary": {m: {"screening": screen(m), "loop": agg(m, "loop"), "strict": agg(m, "strict"), "gentle": agg(m, "gentle"),
                           "icons": {k: v for k, v in icons[m].items() if k != "rows"},
                           "cost": {"loop_usd": round(sum(x["cost"]["loop_usd"] for x in per[m]), 4),
                                    "choice_usd": round(sum(x["cost"]["choice_usd"] for x in per[m]), 4),
                                    "new_calls": sum(x["cost"]["new_calls"] for x in per[m])}} for m in ("names", "codes")},
           "icons": icons, "icon_test_cost": {**cost, "usd": round(cost["tokens"] * PRICE_IN, 4)}}
    json.dump(out, open(os.path.join(a.outdir, "summary.json"), "w"), indent=1, default=float)
    m_.extra.update({"summary": out["summary"]}); m_.write(os.path.join(a.outdir, "manifest.json"), outputs=["summary.json"])
    print(json.dumps(out["summary"], indent=1))
