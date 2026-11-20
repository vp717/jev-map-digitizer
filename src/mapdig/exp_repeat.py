"""Stage `exp-repeat`: is Jev flaky? Ask the same Choice many times, byte-identical each time.

Takes the most uncertain medical icons from exp-anon's 119-icon test (lowest probability on
the true class in either label mode) and repeats the 31-row Choice --repeats times per icon,
in both label modes. The request sent is identical every time; only the cache key carries the
repeat number, so every answer is stored and the run replays offline.
"""
import collections, io, json, os

def add_args(p):
    p.add_argument("--anon-summary", required=True, help="exp_anon/summary.json")
    p.add_argument("--symbols", required=True)
    p.add_argument("--icons", type=int, default=10)
    p.add_argument("--repeats", type=int, default=30)
    p.add_argument("--cache", default="cache/api")
    p.add_argument("--api-mode", default="online", choices=["online", "offline", "refresh"])
    p.add_argument("--outdir", required=True)

def run(a):
    import hashlib
    import numpy as np
    from PIL import Image
    from mapdig.apicache import ApiCache
    from mapdig.jev import Jev, PRICE_IN
    from mapdig.labels import anonymize
    from mapdig.manifest import Manifest

    m_ = Manifest("exp-repeat", {k: v for k, v in vars(a).items() if k != "stage"}, inputs=[a.anon_summary, a.symbols])
    os.makedirs(a.outdir, exist_ok=True)
    A = json.load(open(a.anon_summary)); adir = os.path.dirname(a.anon_summary)
    rn = {q["k"]: q for q in A["icons"]["names"]["rows"]}; rc = {q["k"]: q for q in A["icons"]["codes"]["rows"]}
    pick = sorted(rn, key=lambda k: min(rn[k]["p_true"], rc[k]["p_true"]))[:a.icons]
    sym = json.load(open(a.symbols)); sdir = os.path.dirname(a.symbols)
    ents = [e for e in sym["entries"] if e["crop"]]
    def png(im):
        b = io.BytesIO(); im.save(b, "PNG"); return b.getvalue()
    def pad(im):
        side = max(280, im.width, im.height); c = Image.new("RGB", (side, side), (242, 239, 233))
        c.paste(im, ((side - im.width) // 2, (side - im.height) // 2)); return c
    def legend(e):
        ic = Image.open(os.path.join(sdir, e["crop"])).convert("RGB"); return png(pad(ic.resize((ic.width * 8, ic.height * 8), Image.LANCZOS)))
    cache = ApiCache(a.cache, a.api_mode); jev = Jev(cache)
    tokens = 0; results = []
    for k in pick:
        crop = open(os.path.join(adir, "icons", f"{k:04d}.png"), "rb").read()   # the exact crop used in exp-anon
        rec = {"k": k, "truth": rn[k]["truth"], "first": {"names": rn[k]["choice_class"], "codes": rc[k]["choice_class"]}}
        for mode in ("names", "codes"):
            es = anonymize(ents) if mode == "codes" else ents
            opts = [(e["label"], legend(e)) for e in es]; row_class = {e["label"]: e["gt_label"] for e in es}
            picks, p_true, distinct = collections.Counter(), [], set()
            for i in range(a.repeats):
                e = jev.which_symbol(crop, opts, repeat=i)   # repeat 0 is the original exp-anon call
                tokens += e["usage"]["input_tokens"] if i else 0
                ans = e["response"]["answers"]["which"]; probs = ans.get("probabilities") or {}
                picks[row_class.get(ans["choice"]) or "none"] += 1
                p_true.append(sum(v for kk, v in probs.items() if row_class.get(kk) == rn[k]["truth"]))
                distinct.add(hashlib.sha256(json.dumps(ans, sort_keys=True).encode()).hexdigest())
            rec[mode] = {"picks": dict(picks.most_common()), "right": picks[rn[k]["truth"]], "n": a.repeats,
                         "p_true_mean": round(float(np.mean(p_true)), 3), "p_true_min": round(float(np.min(p_true)), 3),
                         "p_true_max": round(float(np.max(p_true)), 3), "distinct_answers": len(distinct)}
        results.append(rec)
        print(f"{k} {rec['truth']:<16} names {rec['names']['right']:>2}/{a.repeats} {rec['names']['picks']}  "
              f"codes {rec['codes']['right']:>2}/{a.repeats} {rec['codes']['picks']}", flush=True)
    out = {"icons": results, "repeats": a.repeats, "new_calls": cache.calls, "cache_hits": cache.hits,
           "usd": round(tokens * PRICE_IN, 4)}
    json.dump(out, open(os.path.join(a.outdir, "summary.json"), "w"), indent=1)
    m_.extra.update({k: out[k] for k in ("new_calls", "usd")}); m_.write(os.path.join(a.outdir, "manifest.json"), outputs=["summary.json"])
