"""Stage `exp-vote` (change 7): repeat the class decision when Jev is unsure.

Same detections, crops and 31-row Choice as choice-check (change 5). Up to 5 byte-identical
calls per detection (call 0 is the original choice-check call; the repeat number only enters
the cache key). Strategies, all scored by class with the strict and gentle rules:
  single    call 0 only (= change 5)
  adaptive  call 0; if its top probability < --threshold, add calls 1-2 and vote; if no class
            has 2 of 3 votes, add calls 3-4 and vote over 5
  vote3     calls 0-2, majority
  vote5     calls 0-4, majority
Ties are broken by the summed probability on each class.
"""
import collections, io, json, os

LAND = (242, 239, 233)

def add_args(p):
    p.add_argument("--map", required=True)
    p.add_argument("--symbols", required=True)
    p.add_argument("--demo-report", required=True)
    p.add_argument("--threshold", type=float, default=0.95)
    p.add_argument("--margin", type=int, default=3)
    p.add_argument("--match-px", type=float, default=7)
    p.add_argument("--cache", default="cache/api")
    p.add_argument("--api-mode", default="online", choices=["online", "offline", "refresh"])
    p.add_argument("--outdir", required=True)

def run(a):
    import numpy as np, rasterio
    from PIL import Image
    from rasterio.windows import Window
    from mapdig.apicache import ApiCache
    from mapdig.choice_check import match
    from mapdig.jev import Jev, PRICE_IN
    from mapdig.manifest import Manifest

    m_ = Manifest("exp-vote", {k: v for k, v in vars(a).items() if k != "stage"}, inputs=[a.map, a.symbols, a.demo_report])
    os.makedirs(a.outdir, exist_ok=True)
    def png(im):
        b = io.BytesIO(); im.save(b, "PNG"); return b.getvalue()
    def pad(im):
        side = max(280, im.width, im.height)
        c = Image.new("RGB", (side, side), LAND); c.paste(im, ((side - im.width) // 2, (side - im.height) // 2)); return c
    sym = json.load(open(a.symbols)); sdir = os.path.dirname(a.symbols)
    entries = [e for e in sym["entries"] if e["crop"]]
    row_class = {e["label"]: e["gt_label"] for e in entries}
    def legend(e):
        icon = Image.open(os.path.join(sdir, e["crop"])).convert("RGB")
        return png(pad(icon.resize((icon.width * 8, icon.height * 8), Image.LANCZOS)))
    opts = [(e["label"], legend(e)) for e in entries]
    r = json.load(open(a.demo_report)); tx, ty = r["tile"]["x"], r["tile"]["y"]
    boxes = {(s["label"], tuple(s["sub"]), s["pass"]): s["box"] for s in r["loop"] if s["action"].startswith("detect")}
    src = rasterio.open(a.map)
    cache = ApiCache(a.cache, a.api_mode); jev = Jev(cache)
    tok_per_call = []

    def vote(ans):
        cnt = collections.Counter(x["cls"] for x in ans); psum = collections.defaultdict(float)
        for x in ans:
            for c, p in x["p_by_class"].items():
                psum[c] += p
        best = max(cnt, key=lambda c: (cnt[c], psum.get(c, 0.0)))
        return best, cnt[best]

    rows = []
    for i, pr in enumerate(r["predictions"]):
        b = boxes[(pr["label"], tuple(pr["sub"]), pr["pass_index"])]
        x0, y0 = int(np.floor(tx + b[0])) - a.margin, int(np.floor(ty + b[1])) - a.margin
        x1, y1 = int(np.ceil(tx + b[2])) + a.margin, int(np.ceil(ty + b[3])) + a.margin
        im = Image.fromarray(np.moveaxis(src.read((1, 2, 3), window=Window(x0, y0, x1 - x0, y1 - y0), boundless=True), 0, -1))
        crop = png(pad(im.resize((im.width * 8, im.height * 8), Image.LANCZOS)))
        ans = []
        for k in range(5):
            e = jev.which_symbol(crop, opts, repeat=k)
            tok_per_call.append(e["usage"]["input_tokens"])
            w = e["response"]["answers"]["which"]; probs = w.get("probabilities") or {}
            pbc = collections.defaultdict(float)
            for lab, p in probs.items():
                pbc[row_class.get(lab, "none")] += p
            ans.append({"cls": row_class.get(w["choice"], "none"), "row": w["choice"],
                        "top": round(max(probs.values()), 3) if probs else None, "p_by_class": dict(pbc)})
        single = ans[0]["cls"]
        if ans[0]["top"] is not None and ans[0]["top"] >= a.threshold:
            adaptive, n_ad = single, 1
        else:
            c3, k3 = vote(ans[:3])
            adaptive, n_ad = (c3, 3) if k3 >= 2 else (vote(ans)[0], 5)
        rows.append({**{k: pr[k] for k in ("label", "gt_label", "x", "y", "match")},
                     "answers": [{k: x[k] for k in ("cls", "row", "top")} for x in ans],
                     "decision": {"single": single, "adaptive": adaptive, "vote3": vote(ans[:3])[0], "vote5": vote(ans)[0]},
                     "calls": {"single": 1, "adaptive": n_ad, "vote3": 3, "vote5": 5}})
    truth = r["truth"]; tok = float(np.mean(tok_per_call))
    out = {"threshold": a.threshold, "n": len(rows), "rows": rows, "strategies": {}}
    for s in ("single", "adaptive", "vote3", "vote5"):
        strict = [q for q in rows if q["decision"][s] == q["gt_label"]]
        gentle = [q for q in rows if q["decision"][s] in (q["gt_label"], "none")]
        calls = sum(q["calls"][s] for q in rows)
        out["strategies"][s] = {"calls": calls, "usd": round(calls * tok * PRICE_IN, 4),
                                "strict": {k: v for k, v in match(strict, truth, a.match_px).items() if k != "by_appearance"},
                                "gentle": {k: v for k, v in match(gentle, truth, a.match_px).items() if k != "by_appearance"}}
    out["loop"] = {k: v for k, v in match(r["predictions"], truth, a.match_px).items() if k != "by_appearance"}
    out["api_new_calls"] = cache.calls; out["api_cache_hits"] = cache.hits
    json.dump(out, open(os.path.join(a.outdir, "summary.json"), "w"), indent=1, default=float)
    m_.extra.update({"strategies": out["strategies"], "api_new_calls": cache.calls})
    m_.write(os.path.join(a.outdir, "manifest.json"), outputs=["summary.json"])
    print(json.dumps(out["strategies"], indent=1), out["api_new_calls"], out["api_cache_hits"])
