"""Command `runlog`: build the run-log page (one tab per run or method change) from run outputs.

Each entry in TABS is a builder that reads committed-pipeline outputs, writes the images it
needs under <out>/img and returns a JSON-able dict. The page template is
src/mapdig/templates/runlog.html; the data is inlined so the page is self-contained apart
from images. Add a builder + a panel in the template for every new change.
"""
import collections, csv, io, json, os, shutil

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

    # ---------- tab 6: change 5, full labels + appearance-variant legend rows ----------
    E5 = E + "_v2"
    C5 = json.load(open(f"{E5}/choice_check/summary.json"))
    r5 = json.load(open(f"{E5}/demo_tile/report.json"))
    sym5 = json.load(open(f"{E5}/legend_read/z17_s1/symbols.json"))
    rows5 = list(csv.DictReader(open("config/osm_classes_z17_v2.csv")))
    old_rows = {q["file"]: q["label"] for q in csv.DictReader(open("config/osm_classes_z17_dance.csv"))}
    renames = [{"file": q["file"], "old": old_rows[q["file"]], "new": q["label"]} for q in rows5
               if not q["appearance"] or q["label"] == "Picnic site"]
    renames = [x for x in renames if x["old"] != x["new"]]
    variant_imgs = []
    for e in sym5["entries"]:
        if e.get("gt_appearance") or e["label"] in ("Picnic site",):
            variant_imgs.append({"label": e["label"], "class": e["gt_label"], "appearance": e.get("gt_appearance", ""),
                                 "img": pngf(open_(f"{E5}/legend_read/z17_s1/{e['crop']}"), f"c5_row{e['index']:02d}.png", 6)})
    base_of = {}
    for e in sym5["entries"]:
        if not e.get("gt_appearance") and e["gt_label"] in {v["class"] for v in variant_imgs}:
            base_of[e["gt_label"]] = pngf(open_(f"{E5}/legend_read/z17_s1/{e['crop']}"), f"c5_base{e['index']:02d}.png", 6)
    for v in variant_imgs:
        if v["label"] == "Picnic site":   # the picnic class's base row has an explicit (green) appearance
            base_of.setdefault(v["class"], v["img"])
    for v in variant_imgs:
        v["base_img"] = base_of.get(v["class"])
    c5 = {"choice": {k: C5[k] for k in ("loop", "strict", "gentle", "cost", "n_options", "api_new_calls")},
          "c4": {k: S4["A"][k] for k in ("loop", "strict", "gentle")}, "renames": renames, "variants": variant_imgs,
          "opus": sym5["summary"], "demo_cost": r5["cost"],
          "screen_missed": [{"label": x["label"], "p": x["p_present"], "n": x["n_true"]} for x in r5["screening"] if x["n_true"] and not x["screened_in"]],
          "sheet": pngf(open_(f"{E5}/legend/z17_s1/sheet.png"), "c5_sheet.png", 1),
          "rows_lost": [q for q in C5["rows"] if q["match"] == "TP" and not q["strict"]],
          "manifest": manifest(f"{E5}/choice_check/manifest.json")}

    # ---------- tab 7: change 6, legend names vs arbitrary codes (medical classes) ----------
    from mapdig.labels import anonymize
    A6 = json.load(open(f"{E5}/exp_anon/summary.json"))
    src5 = rasterio.open(f"{E5}/maps/freiburg_centre/z17_s1/map.tif")
    tiles6 = []
    for i, t in enumerate(A6["tiles"]):
        rgb = np.moveaxis(src5.read((1, 2, 3), window=Window(t["x"], t["y"], 640, 640)), 0, -1)
        tiles6.append({**t, "img": jpg(Image.fromarray(rgb), f"c6_tile{i}.jpg", 240)})
    codes = {e["name"]: e["label"] for e in anonymize([e for e in sym5["entries"] if e["crop"]])}
    rn = {q["k"]: q for q in A6["icons"]["names"]["rows"]}; rc = {q["k"]: q for q in A6["icons"]["codes"]["rows"]}
    flips = {"names_wrong": [], "codes_wrong": []}
    for k in rn:
        n_ok, c_ok = rn[k]["choice_class"] == rn[k]["truth"], rc[k]["choice_class"] == rc[k]["truth"]
        key = "names_wrong" if (c_ok and not n_ok) else "codes_wrong" if (n_ok and not c_ok) else None
        if key and len(flips[key]) < 8:
            flips[key].append({"truth": rn[k]["truth"], "names": rn[k]["choice_class"], "codes": rc[k]["choice_class"],
                               "img": jpg(open_(f"{E5}/exp_anon/icons/{k:04d}.png"), f"c6_icon{k:04d}.jpg", 140)})
    agree = {"both": 0, "only_names": 0, "only_codes": 0, "neither": 0}
    for k in rn:
        n_ok, c_ok = rn[k]["choice_class"] == rn[k]["truth"], rc[k]["choice_class"] == rc[k]["truth"]
        agree["both" if n_ok and c_ok else "only_names" if n_ok else "only_codes" if c_ok else "neither"] += 1
    def lost(mode):
        cnt = collections.Counter()
        for t in A6["per_tile"][mode]:
            for q in t["choices"]:
                if q["match"] == "TP" and q["choice_class"] != q["gt_label"]:
                    cnt[f"{q['gt_label']} → {q['choice_class'] or 'none'}"] += 1
        return dict(cnt)
    def loopfp(mode):
        cnt = collections.Counter()
        for t in A6["per_tile"][mode]:
            for q in t["choices"]:
                if q["match"] == "FP":
                    cnt[q["gt_label"]] += 1
        return dict(cnt)
    c6 = {"summary": A6["summary"], "tiles": tiles6, "flips": flips, "agree": agree,
          "codes": [{"name": n, "code": c} for n, c in codes.items()], "icon_cost": A6["icon_test_cost"],
          "lost": {m: lost(m) for m in ("names", "codes")}, "loopfp": {m: loopfp(m) for m in ("names", "codes")},
          "manifest": manifest(f"{E5}/exp_anon/manifest.json")}

    # ---------- tab 8: change 7, repeat the class decision when unsure ----------
    V7 = json.load(open(f"{E5}/exp_vote/summary.json"))
    changed7 = []
    for i, q in enumerate(V7["rows"]):
        if len(set(q["decision"].values())) > 1:
            changed7.append({**{k: q[k] for k in ("gt_label", "match", "decision", "answers", "calls")},
                             "img": jpg(open_(f"{E5}/choice_check/crops/{i:02d}.png"), f"c7_crop{i:02d}.jpg", 150)})
    tops = [q["answers"][0]["top"] for q in V7["rows"]]
    c7 = {"strategies": V7["strategies"], "threshold": V7["threshold"], "n": V7["n"], "changed": changed7,
          "n_unsure": sum(q["calls"]["adaptive"] > 1 for q in V7["rows"]),
          "n_five": sum(q["calls"]["adaptive"] == 5 for q in V7["rows"]),
          "api_new_calls": V7["api_new_calls"], "manifest": manifest(f"{E5}/exp_vote/manifest.json"),
          "fp_strict": [{"label": q["gt_label"], "answers": [x["cls"] for x in q["answers"]], "top": q["answers"][0]["top"]}
                        for q in V7["rows"] if q["match"] == "FP" and q["decision"]["single"] == q["gt_label"]]}

    # ---------- tab 9: change 8, colour-mask the search images to each symbol's palette ----------
    from mapdig.palette import mask_image, effective_palette
    PAL = json.load(open(f"{E5}/palette/palette.json")); palc = {x["label"]: x["colours"] for x in PAL["entries"]}
    sd5 = f"{E5}/legend_read/z17_s1"
    R8 = {m: json.load(open(f)) for m, f in (("none", f"{E5}/demo_tile/report.json"), ("core", f"{E5}/demo_tile_mask_core/report.json"),
                                             ("unmix", f"{E5}/demo_tile_mask_unmix/report.json"))}
    V8 = {m: json.load(open(f)) for m, f in (("none", f"{E5}/exp_vote/summary.json"), ("core", f"{E5}/exp_vote_mask_core/summary.json"),
                                             ("unmix", f"{E5}/exp_vote_mask_unmix/summary.json"))}
    tx8, ty8 = R8["none"]["tile"]["x"], R8["none"]["tile"]["y"]
    tile8 = np.moveaxis(src5.read((1, 2, 3), window=Window(tx8, ty8, 640, 640)), 0, -1)
    masked_tiles = [{"label": "original tile", "img": jpg(Image.fromarray(tile8), "c8_tile.jpg", 400)}]
    for lab in ("Doctor / clinic", "Supermarket", "Traffic signals"):
        masked_tiles.append({"label": f"masked for {lab}", "img": jpg(Image.fromarray(mask_image(tile8, palc[lab], 12)), f"c8_tile_{lab[:5].strip().lower()}.jpg", 400)})
    leg_rows = []
    for e in [x for x in json.load(open(f"{sd5}/symbols.json"))["entries"] if x["crop"]]:
        leg = np.asarray(Image.open(f"{sd5}/{e['crop']}").convert("RGB"))
        leg = np.pad(leg, ((3, 3), (3, 3), (0, 0)), constant_values=0); leg[:3] = leg[-3:] = leg[:, :3] = leg[:, -3:] = (242, 239, 233)
        pe = next(x for x in PAL["entries"] if x["label"] == e["label"])
        leg_rows.append({"label": e["label"], "colours": pe["colours"], "kept": effective_palette(pe["colours"], 12),
                         "true": pe["true_fill_as_drawn"], "de": pe["delta_e_nearest"],
                         "orig": pngf(Image.fromarray(leg), f"c8_leg{e['index']:02d}_o.png", 6),
                         "core": pngf(Image.fromarray(mask_image(leg, pe["colours"], 12, edges=False)), f"c8_leg{e['index']:02d}_c.png", 6),
                         "unmix": pngf(Image.fromarray(mask_image(leg, pe["colours"], 12)), f"c8_leg{e['index']:02d}_u.png", 6)})
    def screen_missed(rep):   # classes on the tile for which no legend row screened in
        by = collections.defaultdict(list)
        for x in rep["screening"]:
            by[x["gt_label"]].append(x)
        return [c for c, xs in by.items() if xs[0]["n_true"] > 0 and not any(x["screened_in"] for x in xs)]
    variants = {}
    for m in R8:
        variants[m] = {"loop": {k: R8[m]["metrics"][k] for k in ("tp", "fp", "fn", "precision", "recall", "f1")},
                       "missed": screen_missed(R8[m]), "loop_calls": R8[m]["cost"]["jev_calls"], "loop_usd": R8[m]["cost"]["jev_usd"],
                       "single": V8[m]["strategies"]["single"], "adaptive": V8[m]["strategies"]["adaptive"], "vote5": V8[m]["strategies"]["vote5"]}
    per8 = []
    for c, a in R8["none"]["metrics"]["per_class"].items():
        b, d = R8["core"]["metrics"]["per_class"].get(c, {}), R8["unmix"]["metrics"]["per_class"].get(c, {})
        if not (a == b == d):
            per8.append({"cls": c, "true": a["true"], "none": [a["tp"], a["pred"]], "core": [b.get("tp", 0), b.get("pred", 0)], "unmix": [d.get("tp", 0), d.get("pred", 0)]})
    c8 = {"variants": variants, "per_class": per8, "tiles": masked_tiles, "legend": leg_rows, "palette_cost": PAL["cost_usd"],
          "new_calls": sum(R8[m]["cost"]["api_new_calls"] + V8[m]["api_new_calls"] for m in ("core", "unmix")),
          "manifest": manifest(f"{E5}/demo_tile_mask_unmix/manifest.json")}

    data = {"tabs": [{"id": "run-1", "title": "Run 1 · baseline", "date": "2026-11-20"},
                     {"id": "change-1", "title": "Change 1 · batched screening", "date": "2026-11-20"},
                     {"id": "change-2", "title": "Change 2 · Choice check", "date": "2026-11-20"},
                     {"id": "change-3", "title": "Change 3 · tighter crops", "date": "2026-11-20"},
                     {"id": "change-4", "title": "Change 4 · Fitness vs Dance", "date": "2026-11-20"},
                     {"id": "change-5", "title": "Change 5 · full names + variants", "date": "2026-11-20"},
                     {"id": "change-6", "title": "Change 6 · names vs codes", "date": "2026-11-20"},
                     {"id": "change-7", "title": "Change 7 · ask again when unsure", "date": "2026-11-20"},
                     {"id": "change-8", "title": "Change 8 · colour mask", "date": "2026-11-20"}],
            "base": base, "c1": c1, "c2": c2, "c3": c3, "c4": c4, "c5": c5, "c6": c6, "c7": c7, "c8": c8}
    tpl = open(os.path.join(os.path.dirname(__file__), "templates", "runlog.html")).read()
    open(os.path.join(O, "index.html"), "w").write(tpl.replace("/*DATA*/null", json.dumps(data, separators=(",", ":"))))
    files = sorted("img/" + f for f in os.listdir(I))
    json.dump(files, open(os.path.join(O, "files.json"), "w"))
    print(f"{O}/index.html, {len(files)} images")
