"""Stage `noise-summary`: run-to-run spread of the whole search + class decision.

Reads noise/<mask>/r<rep>/{report.json, vote/summary.json} (byte-identical requests, repeat
number in the cache key only) and scores each run with faded "restricted access" icons excluded
(faded truth removed; detections on them or from faded legend rows ignored). Reports per-run
F1, per-icon consistency (found in k of n runs) and box-centre spread for the same icon.
"""
import collections, json, os

def add_args(p):
    p.add_argument("--noise-dir", required=True)
    p.add_argument("--masks", nargs="+", default=["none", "unmix"])
    p.add_argument("--reps", type=int, default=3)
    p.add_argument("--match-px", type=float, default=7)
    p.add_argument("--out", required=True)

def run(a):
    import numpy as np
    from mapdig.choice_check import match
    out = {"masks": {}}
    for m in a.masks:
        runs, found, cent = [], [], []
        for r in range(a.reps):
            d = os.path.join(a.noise_dir, m, f"r{r}")
            R = json.load(open(os.path.join(d, "report.json"))); V = json.load(open(os.path.join(d, "vote", "summary.json")))
            truth = R["truth"]; faded = [t for t in truth if "@" in (t.get("appearance") or "")]
            keep = [t for t in truth if t not in faded]
            def drop(p):
                return "restricted access" in p["label"] or any(
                    f["label"] == p["gt_label"] and np.hypot(f["x"] - p["x"], f["y"] - p["y"]) <= a.match_px for f in faded)
            idx = [i for i, p in enumerate(R["predictions"]) if not drop(p)]
            preds = [R["predictions"][i] for i in idx]; rows = [V["rows"][i] for i in idx]
            lp = match(preds, keep, a.match_px)
            ad = match([q for q in rows if q["decision"]["adaptive"] == q["gt_label"]], keep, a.match_px)
            pairs = sorted((float(np.hypot(p["x"] - t["x"], p["y"] - t["y"])), i, j)
                           for i, p in enumerate(preds) for j, t in enumerate(keep) if p["gt_label"] == t["label"])
            up, ut, c = set(), set(), {}
            for dd, i, j in pairs:
                if dd <= a.match_px and i not in up and j not in ut:
                    up.add(i); ut.add(j); c[j] = (preds[i]["x"], preds[i]["y"])
            present = {s["gt_label"] for s in R["screening"] if s["n_true"] > 0 and "restricted access" not in s["label"]}
            missed = sorted(present - {s["gt_label"] for s in R["screening"] if s["screened_in"]})
            found.append(ut); cent.append(c); n = len(keep); labels = [t["label"] for t in keep]
            strip = lambda x: {k: v for k, v in x.items() if k != "by_appearance"}
            runs.append({"rep": r, "loop": strip(lp), "adaptive": strip(ad), "screen_missed": missed,
                         "new_calls": R["cost"]["api_new_calls"] + V["api_new_calls"],
                         "usd": round(R["cost"]["jev_usd"] + V["strategies"]["adaptive"]["usd"], 4)})
        k_found = collections.Counter(sum(j in f for f in found) for j in range(n))
        flaky = collections.Counter(labels[j] for j in range(n) if 0 < sum(j in f for f in found) < a.reps)
        jit = []
        for j in range(n):
            cs = np.array([c[j] for c in cent if j in c])
            if len(cs) >= 2:
                jit.append(float(np.max(np.linalg.norm(cs - cs.mean(0), axis=1))))
        lf = [x["loop"]["f1"] for x in runs]; af = [x["adaptive"]["f1"] for x in runs]
        out["masks"][m] = {"runs": runs, "n_truth": n,
                           "loop_f1": {"mean": round(float(np.mean(lf)), 3), "min": min(lf), "max": max(lf)},
                           "adaptive_f1": {"mean": round(float(np.mean(af)), 3), "min": min(af), "max": max(af)},
                           "found_k_of_n": {str(k): k_found.get(k, 0) for k in range(a.reps, -1, -1)},
                           "flaky_by_class": dict(flaky.most_common()),
                           "centre_spread_px": {"median": round(float(np.median(jit)), 2), "p90": round(float(np.percentile(jit, 90)), 2)}}
    json.dump(out, open(a.out, "w"), indent=1)
    print(json.dumps({m: {k: v for k, v in x.items() if k != "runs"} for m, x in out["masks"].items()}, indent=1))
