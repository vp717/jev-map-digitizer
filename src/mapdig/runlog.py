"""Command `runlog`: build the run-log page (one tab per run or method change) from run outputs.

Each entry in TABS is a builder that reads committed-pipeline outputs, writes the images it
needs under <out>/img and returns a JSON-able dict. The page template is
src/mapdig/templates/runlog.html; the data is inlined so the page is self-contained apart
from images. Add a builder + a panel in the template for every new change.
"""
import csv, io, json, os, shutil

def add_args(p):
    p.add_argument("--exp", default="out/osm_phase1")
    p.add_argument("--out", default="out/runlog")

def run(a):
    import numpy as np, rasterio
    from PIL import Image, ImageDraw
    from rasterio.windows import Window

    E, O = a.exp, a.out
    I = os.path.join(O, "img")
    shutil.rmtree(O, ignore_errors=True); os.makedirs(I)
    def jpg(im, name, w=None, q=86):
        im = im.convert("RGB")
        if w and im.width > w:
            im = im.resize((w, round(im.height * w / im.width)), Image.LANCZOS)
        im.save(os.path.join(I, name), "JPEG", quality=q, optimize=True); return f"img/{name}"
    def pngf(im, name, scale=1):
        im = im.convert("RGB")
        if scale != 1:
            im = im.resize((im.width * scale, im.height * scale), Image.NEAREST)
        im.save(os.path.join(I, name), "PNG", optimize=True); return f"img/{name}"
    open_ = lambda p: Image.open(p)
    land = (242, 239, 233)
    sym = json.load(open(f"{E}/legend_read/z17_s1/symbols.json"))
    sdir = f"{E}/legend_read/z17_s1"
    entries = [e for e in sym["entries"] if e["crop"]]
    def legend(e, k):
        icon = Image.open(os.path.join(sdir, e["crop"])).convert("RGB")
        icon = icon.resize((icon.width * k, icon.height * k), Image.LANCZOS)
        side = max(280, icon.width + 8, icon.height + 8)
        c = Image.new("RGB", (side, side), land); c.paste(icon, ((side - icon.width) // 2, (side - icon.height) // 2))
        return c
    mapf = f"{E}/maps/freiburg_centre/z17_s1/map.tif"
    src = rasterio.open(mapf)
    def manifest(path):
        try:
            m = json.load(open(path)); return {"commit": m["git"]["commit"][:7], "dirty": m["git"]["dirty"], "started": m["started_utc"]}
        except Exception:
            return None

    # ---------- tab 1: baseline single-tile run ----------
    D = f"{E}/demo_tile"; r = json.load(open(f"{D}/report.json"))
    base = {"tile": r["tile"], "metrics": r["metrics"], "cost": r["cost"], "timing_s": r["timing_s"], "legend": r["legend"],
            "screening": [{k: s.get(k) for k in ("label", "p_present", "n_true", "screened_in")} for s in r["screening"]],
            "actions": {}, "manifest": manifest(f"{D}/manifest.json")}
    for st in r["loop"]:
        base["actions"][st["action"]] = base["actions"].get(st["action"], 0) + 1
    base["images"] = {
        "overview": jpg(open_(f"{D}/img/00_overview.png"), "b_overview.jpg", 1100),
        "tile": pngf(open_(f"{D}/img/01_tile.png"), "b_tile.png"),
        "result": jpg(open_(f"{D}/img/09_result.png"), "b_result.jpg", 1280, 90),
        "legend_sheet": pngf(open_(f"{E}/legend/z17_s1/sheet.png"), "b_legend_sheet.png", 2),
        "legend_read": pngf(open_(f"{sdir}/read_overlay.png"), "b_legend_read.png"),
        "memorial_after": pngf(open_(f"{D}/{next(s for s in r['screening'] if s['label'] == 'Memorial')['work_image']}"), "b_memorial_after.png"),
    }
    base["crops"] = [{"label": e["label"], "img": pngf(open_(os.path.join(sdir, e["crop"])), f"b_crop_{e['index']:02d}.png", 4),
                      "iou_read": e["iou_read"], "iou_crop": e["iou_crop"]} for e in sym["entries"]]
    match = {(p["label"], tuple(p["sub"]), p["pass_index"]): p["match"] for p in r["predictions"]}
    want = {"Doctor": 3, "Memorial": 2, "Statue": 2, "Traffic signals": 2, "Fitness station": 2}
    frames = []
    for f in r["frames"]:
        m = match.get((f["label"], tuple(f["sub"]), f["pass"]), "merged"); k = f["label"]
        if want.get(k, 0) and (k not in ("Statue", "Fitness station", "Traffic signals") or m == "FP" or not any(x["label"] == k for x in frames)):
            want[k] -= 1; n = len(frames)
            frames.append({**{q: f[q] for q in ("label", "sub", "pass", "p_present", "box_conf")}, "match": m,
                           "before": jpg(open_(f"{D}/{f['before']}"), f"b_frame{n:02d}_a.jpg", 400, 88),
                           "after": jpg(open_(f"{D}/{f['after']}"), f"b_frame{n:02d}_b.jpg", 400, 88)})
    base["frames"] = frames

    # why each false positive was scored wrong (same logic for every tab)
    def fp_reason(pr):
        if pr["match"] == "TP":
            return {"kind": "correct", "text": "scored correct: within 7 px of a true icon of this class"}
        same = sorted(float(np.hypot(pr["x"] - t["x"], pr["y"] - t["y"])) for t in r["truth"] if t["label"] == pr["gt_label"])
        anyc = sorted((float(np.hypot(pr["x"] - t["x"], pr["y"] - t["y"])), t["label"]) for t in r["truth"])
        if same and same[0] <= 7:
            return {"kind": "duplicate", "text": f"duplicate: a {pr['gt_label']} {same[0]:.1f} px away was already matched by another detection"}
        if anyc and anyc[0][0] <= 7 and anyc[0][1] != pr["gt_label"]:
            return {"kind": "wrong class", "text": f"wrong class: the icon here is a {anyc[0][1]} ({anyc[0][0]:.1f} px), not a {pr['gt_label']}"}
        if same and same[0] <= 15:
            return {"kind": "off-centre", "text": f"off-centre: the nearest {pr['gt_label']} is {same[0]:.1f} px away (limit 7 px)"}
        return {"kind": "nothing nearby", "text": f"nothing there: no true {pr['gt_label']} within 15 px"}
    reasons = [fp_reason(pr) for pr in r["predictions"]]
    base["fp_reasons"] = {}
    for q in reasons:
        if q["kind"] != "correct":
            base["fp_reasons"][q["kind"]] = base["fp_reasons"].get(q["kind"], 0) + 1

    # ---------- tabs 2 and 3: from the multi-image experiment ----------
    X = f"{E}/exp_multiimage"; S = json.load(open(f"{X}/summary.json"))
    rows = list(csv.DictReader(open(f"{X}/screening.csv")))
    for row in rows:
        for k in ("tile", "x", "y", "n_true"): row[k] = int(row[k])
        for k in ("p_single", "p_batch"): row[k] = float(row[k])
    tiles = sorted({(row["tile"], row["x"], row["y"]) for row in rows})
    W, H = src.width, src.height
    sc = 1000 / W
    ov = Image.fromarray(np.moveaxis(src.read((1, 2, 3), out_shape=(3, int(H * sc), 1000)), 0, -1)); dr = ImageDraw.Draw(ov)
    per_tile = []
    for ti, x, y in tiles:
        dr.rectangle([x * sc, y * sc, (x + 640) * sc, (y + 640) * sc], outline="#c2187a", width=3)
        dr.text((x * sc + 5, y * sc + 3), str(ti), fill="#c2187a")
        rgb = np.moveaxis(src.read((1, 2, 3), window=Window(x, y, 640, 640)), 0, -1)
        tr = [q for q in rows if q["tile"] == ti]
        acc = lambda key: sum((q[key] >= 0.5) == (q["n_true"] > 0) for q in tr) / len(tr)
        per_tile.append({"tile": ti, "x": x, "y": y, "present": sum(q["n_true"] > 0 for q in tr), "icons": sum(q["n_true"] for q in tr),
                         "acc_single": round(acc("p_single"), 2), "acc_batch": round(acc("p_batch"), 2),
                         "disagree": sum((q["p_single"] >= 0.5) != (q["p_batch"] >= 0.5) for q in tr),
                         "img": jpg(Image.fromarray(rgb), f"c1_tile{ti}.jpg", 320)})
    dis = [q for q in rows if (q["p_single"] >= 0.5) != (q["p_batch"] >= 0.5)]
    ex_tile = 6
    doc = next(e for e in entries if e["label"] == "Doctor")
    c1 = {"summary": S["screening"], "per_tile": per_tile, "disagreements": dis, "pairs": rows,
          "overview": jpg(ov, "c1_overview.jpg"),
          "example": {"tile": ex_tile, "img": jpg(Image.fromarray(np.moveaxis(src.read((1, 2, 3), window=Window(
                          *next((t[1], t[2]) for t in tiles if t[0] == ex_tile), 640, 640)), 0, -1)), "c1_example_tile.jpg", 640),
                      "legend": pngf(legend(doc, 2), "c1_example_legend.png"),
                      "row": next(q for q in rows if q["tile"] == ex_tile and q["label"] == "Doctor")},
          "legend_strip": [{"label": e["label"], "img": pngf(legend(e, 2).resize((70, 70), Image.LANCZOS), f"c1_leg{e['index']:02d}.png")} for e in entries],
          "manifest": manifest(f"{X}/manifest.json")}

    C = list(csv.DictReader(open(f"{X}/choice.csv")))
    tx, ty = r["tile"]["x"], r["tile"]["y"]
    big = np.moveaxis(src.read((1, 2, 3), window=Window(tx - 40, ty - 40, 720, 720), boundless=True), 0, -1)
    labels = {e["label"] for e in entries}
    cards = []
    for i, (row, pr) in enumerate(zip(C, r["predictions"])):
        row["keep"] = row["keep"] == "True"
        for k in ("p_own", "p_none", "conf"):
            row[k] = float(row[k]) if row[k] not in ("", "None") else None
        cx, cy = int(round(pr["x"])) + 40, int(round(pr["y"])) + 40
        crop = Image.fromarray(big[cy - 20:cy + 20, cx - 20:cx + 20]).resize((320, 320), Image.LANCZOS)
        row["gentle_keep"] = not (row["choice"] in labels and row["choice"] != row["label"])
        if row["match"] == "FP" or not row["keep"]:
            row["img"] = jpg(crop, f"c2_crop{i:02d}.jpg", 200)
            row["reason"] = reasons[i]
            cards.append(row)
    n_truth = r["metrics"]["tp"] + r["metrics"]["fn"]
    def prf(rs):
        tp = sum(q["match"] == "TP" for q in rs); P = tp / len(rs) if rs else 0; R = tp / n_truth
        return {"pred": len(rs), "tp": tp, "fp": len(rs) - tp, "precision": round(P, 3), "recall": round(R, 3),
                "f1": round(2 * P * R / (P + R), 3) if P + R else 0}
    c2 = {"summary": S["choice"], "before": prf(C), "strict": prf([q for q in C if q["keep"]]),
          "gentle": prf([q for q in C if q["gentle_keep"]]), "cards": cards, "n_truth": n_truth,
          "options": [{"label": e["label"], "img": pngf(legend(e, 8).resize((84, 84), Image.LANCZOS), f"c2_opt{e['index']:02d}.png")} for e in entries],
          "loop_calls": r["cost"]["jev_calls"] - len(r["screening"]), "loop_usd": r["cost"]["jev_usd"],
          "manifest": manifest(f"{X}/manifest.json")}

    # ---------- tab 4: change 3, tighter crops ----------
    Y = f"{E}/exp_crop"; S3 = json.load(open(f"{Y}/summary.json"))
    R3 = list(csv.DictReader(open(f"{Y}/choices.csv")))
    cards3 = []
    for q in R3:
        i = int(q["i"])
        if q["match"] == "FP" or any(q[f"{v}_choice"] != q["label"] for v in ("wide", "box", "sq20")):
            pr = r["predictions"][i]
            cx, cy = int(round(pr["x"])) + 40, int(round(pr["y"])) + 40
            wide = Image.fromarray(big[cy - 20:cy + 20, cx - 20:cx + 20]).resize((320, 320), Image.LANCZOS)
            card = {k: q[k] for k in ("label", "match", "wide_choice", "box_choice", "sq20_choice")}
            card["reason"] = reasons[i]
            card["img"] = {"wide": jpg(wide, f"c3_{i:02d}_wide.jpg", 150),
                           "box": jpg(open_(f"{Y}/crops/{i:02d}_box.png"), f"c3_{i:02d}_box.jpg", 150),
                           "sq20": jpg(open_(f"{Y}/crops/{i:02d}_sq20.png"), f"c3_{i:02d}_sq20.jpg", 150)}
            cards3.append(card)
    ex_i = next(int(q["i"]) for q in R3 if q["label"] == "Statue" and q["match"] == "FP")
    c3 = {"summary": S3, "cards": cards3, "manifest": manifest(f"{Y}/manifest.json"),
          "example": {"label": R3[ex_i]["label"], "wide": f"img/c3_{ex_i:02d}_wide.jpg", "box": f"img/c3_{ex_i:02d}_box.jpg",
                      "sq20": f"img/c3_{ex_i:02d}_sq20.jpg",
                      "option": pngf(legend(next(e for e in entries if e["label"] == "Artwork"), 8).resize((150, 150), Image.LANCZOS), "c3_opt_artwork.png")}}

    # ---------- tab 5: change 4, Dance class added (fair shot for Fitness vs Dance) ----------
    E4 = E + "_dance"
    S4 = json.load(open(f"{E4}/exp_dance/summary.json"))
    r4 = json.load(open(f"{E4}/demo_tile/report.json"))
    sym4 = json.load(open(f"{E4}/legend_read/z17_s1/symbols.json")); sdir4 = f"{E4}/legend_read/z17_s1"
    def icon4(label, name):
        e = next(e for e in sym4["entries"] if e["label"] == label)
        return pngf(open_(os.path.join(sdir4, e["crop"])), name, 8)
    R3c = {int(q["i"]): q for q in R3}
    base_fit = [i for i, pr in enumerate(r["predictions"]) if pr["label"] == "Fitness station" and pr["match"] == "FP"]
    dets = []
    for q in S4["A"]["fd_detections"]:
        i = q["i"]; pr = r4["predictions"][i]
        truth = next((t["label"] for t in r4["truth"] if np.hypot(t["x"] - pr["x"], t["y"] - pr["y"]) <= 7), "nothing")
        dets.append({**{k: q[k] for k in ("label", "match", "choice", "p_fitness", "p_dance")}, "truth": truth,
                     "img": jpg(open_(f"{E4}/exp_dance/crops/det_{i:02d}.png"), f"c4_det{i:02d}.jpg", 160)})
    icons = [{k: q[k] for k in ("truth", "choice26", "choice2", "p26_fitness", "p26_dance", "p2_fitness", "p2_dance")}
             | {"img": jpg(open_(f"{E4}/exp_dance/{q['crop']}"), f"c4_gt{q['k']:04d}.jpg", 120)} for q in S4["B"]["icons"]]
    c4 = {"summary": {k: S4[k] for k in ("cost", "api_new_calls", "api_cache_hits", "dance_screening")},
          "A": {k: S4["A"][k] for k in ("loop", "strict", "gentle")}, "c3_box": S3["box"], "dets": dets, "icons": icons,
          "B26": S4["B"]["choice26"], "B2": S4["B"]["choice2"],
          "opus": sym4["summary"], "truth_icons": r4["tile"]["icons_present"], "base_truth_icons": r["tile"]["icons_present"],
          "demo_cost": r4["cost"], "manifest": manifest(f"{E4}/exp_dance/manifest.json"),
          "legend_fitness": icon4("Fitness station", "c4_leg_fitness.png"), "legend_dance": icon4("Dance", "c4_leg_dance.png"),
          "baseline_fps": [jpg(open_(f"{Y}/crops/{i:02d}_box.png"), f"c4_basefp{i:02d}.jpg", 160) for i in base_fit]}

    data = {"tabs": [{"id": "run-1", "title": "Run 1 · baseline", "date": "2026-11-20"},
                     {"id": "change-1", "title": "Change 1 · batched screening", "date": "2026-11-20"},
                     {"id": "change-2", "title": "Change 2 · Choice check", "date": "2026-11-20"},
                     {"id": "change-3", "title": "Change 3 · tighter crops", "date": "2026-11-20"},
                     {"id": "change-4", "title": "Change 4 · Fitness vs Dance", "date": "2026-11-20"}],
            "base": base, "c1": c1, "c2": c2, "c3": c3, "c4": c4}
    tpl = open(os.path.join(os.path.dirname(__file__), "templates", "runlog.html")).read()
    open(os.path.join(O, "index.html"), "w").write(tpl.replace("/*DATA*/null", json.dumps(data, separators=(",", ":"))))
    files = sorted("img/" + f for f in os.listdir(I))
    json.dump(files, open(os.path.join(O, "files.json"), "w"))
    print(f"{O}/index.html, {len(files)} images")
