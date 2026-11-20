"""Stage `demo-tile`: the whole Jev pipeline on one map tile, saving every intermediate image.

1. Pick a 640 px tile (most distinct classes, or --tile X Y).
2. Stage 1 (screening): for every legend symbol, Noul "present?" on the tile enlarged x2.
3. Stage 2 (search loop): for classes screened in, on 160 px sub-tiles (step 120) enlarged x8:
   Noul+Box -> stop if P(present) < threshold, or the box mostly covers removed area;
   else record the box centre, inpaint the box (cv2.inpaint, Telea) in a per-class working
   copy of the tile, and ask again (max --max-passes per sub-tile).
4. Merge duplicates, georeference, write predictions.gpkg.
5. Score against the render-diff ground truth (one-to-one, same class, <= match px).
Writes report.json and images under --outdir.
"""
import io, json, os, time

def add_args(p):
    p.add_argument("--map", required=True)
    p.add_argument("--gt", required=True)
    p.add_argument("--symbols", required=True, help="read-legend symbols.json (crops next to it)")
    p.add_argument("--tile", nargs=2, type=int, metavar=("X", "Y"), help="tile origin in map px (default: auto)")
    p.add_argument("--tile-px", type=int, default=640)
    p.add_argument("--screen-k", type=int, default=2)
    p.add_argument("--sub-px", type=int, default=160)
    p.add_argument("--sub-step", type=int, default=120)
    p.add_argument("--sub-k", type=int, default=8)
    p.add_argument("--screen-threshold", type=float, default=0.5)
    p.add_argument("--stop-threshold", type=float, default=0.5)
    p.add_argument("--max-passes", type=int, default=8)
    p.add_argument("--match-px", type=float, default=7)
    p.add_argument("--cache", default="cache/api")
    p.add_argument("--api-mode", default="online", choices=["online", "offline", "refresh"])
    p.add_argument("--mask-palette", default=None,
                   help="palette.json from read-palette: show Jev the image masked to each legend row's colours (change 8)")
    p.add_argument("--mask-mode", choices=["core", "unmix"], default="unmix",
                   help="core: palette colours only; unmix: also anti-aliased edge pixels (change 8)")
    p.add_argument("--mask-tol", type=float, default=12.0, help="colour tolerance (CIE76 delta E) for --mask-palette")
    p.add_argument("--label-mode", choices=["names", "codes"], default="names",
                   help="codes: show Jev arbitrary 'symbol NN' codes instead of legend names (change 6)")
    p.add_argument("--only-classes", nargs="*", default=[],
                   help="restrict screening, search and scoring to these classes (ground-truth labels)")
    p.add_argument("--force-classes", nargs="*", default=[],
                   help="legend labels searched by the loop even if screening says no (ablation)")
    p.add_argument("--trace-classes", nargs="*", default=[],
                   help="legend labels whose every Jev call is saved: exact PNG bytes sent, prompt, response")
    p.add_argument("--outdir", required=True)

def run(a):
    import cv2, numpy as np, pyogrio, rasterio, shapely
    from PIL import Image, ImageDraw
    from rasterio.windows import Window
    from mapdig.apicache import ApiCache
    from mapdig.jev import Jev, PRICE_IN as JEV_PRICE
    from mapdig.manifest import Manifest

    m_ = Manifest("demo-tile", {k: v for k, v in vars(a).items() if k != "stage"}, inputs=[a.map, a.gt, a.symbols])
    img_dir = os.path.join(a.outdir, "img"); os.makedirs(img_dir, exist_ok=True)
    def save(im, name):
        im.save(os.path.join(img_dir, name)); return f"img/{name}"
    def png(im):
        b = io.BytesIO(); im.save(b, "PNG"); return b.getvalue()

    src = rasterio.open(a.map)
    W, H, T = src.width, src.height, a.tile_px
    has_app = "appearance" in pyogrio.read_info(a.gt, layer="gt")["fields"]
    _, _, _, f = pyogrio.raw.read(a.gt, layer="gt", columns=["label", "px_x", "px_y"] + (["appearance"] if has_app else []),
                                  read_geometry=False)
    glab, gx, gy = f[0].astype(str), f[1], f[2]
    gapp = f[3].astype(str) if has_app else np.array([""] * len(glab))
    sym = json.load(open(a.symbols))
    sym_dir = os.path.dirname(a.symbols)
    entries = [e for e in sym["entries"] if e["crop"]]
    if a.label_mode == "codes":
        from mapdig.labels import anonymize
        entries = anonymize(entries)
    if a.only_classes:
        entries = [e for e in entries if e["gt_label"] in a.only_classes]
    land = tuple(int(v) for v in np.asarray(Image.open(os.path.join(sym_dir, entries[0]["crop"])).convert("RGB"))[0, 0]) \
        if False else (242, 239, 233)   # openstreetmap-carto land colour #f2efe9

    # 1. tile choice: most distinct ground-truth classes in a T x T window (grid search, step 64)
    if a.tile:
        tx, ty = a.tile
    else:
        best = (-1, 0, 0)
        for ty_ in range(0, H - T + 1, 64):
            for tx_ in range(0, W - T + 1, 64):
                inn = (gx >= tx_ + 8) & (gx < tx_ + T - 8) & (gy >= ty_ + 8) & (gy < ty_ + T - 8)
                score = (len(set(glab[inn])), int(inn.sum()))
                if score > best[:2]:
                    best = (*score, tx_, ty_)
        tx, ty = best[2], best[3]
    tile = np.moveaxis(src.read((1, 2, 3), window=Window(tx, ty, T, T)), 0, -1).copy()
    tf = src.transform
    in_tile = (gx >= tx) & (gx < tx + T) & (gy >= ty) & (gy < ty + T)
    truth = [{"label": l, "x": float(x - tx), "y": float(y - ty), "appearance": ap}
             for l, x, y, ap in zip(glab[in_tile], gx[in_tile], gy[in_tile], gapp[in_tile])]
    if a.only_classes:
        truth = [t for t in truth if t["label"] in a.only_classes]

    # overview: map thumbnail with the tile outlined
    sc = 1200 / W
    ov = Image.fromarray(np.moveaxis(src.read((1, 2, 3), out_shape=(3, int(H * sc), 1200)), 0, -1))
    ImageDraw.Draw(ov).rectangle([tx * sc, ty * sc, (tx + T) * sc, (ty + T) * sc], outline="#e0218a", width=3)
    images = {"overview": save(ov, "00_overview.png"), "tile": save(Image.fromarray(tile), "01_tile.png")}

    cache = ApiCache(a.cache, a.api_mode)
    jev = Jev(cache)
    tokens = {"calls": 0, "input_tokens": 0}
    from mapdig.jev import PROMPTS, _symbol_phrase
    trace = {"screening": {"calls": []}, "loops": {}}
    tdir = os.path.join(a.outdir, "trace")
    if a.trace_classes:
        os.makedirs(tdir, exist_ok=True)
    def tsave(b, name):   # exact bytes that were sent
        open(os.path.join(tdir, name), "wb").write(b); return f"trace/{name}"
    def prompt_text(q, label):
        return PROMPTS[jev.pv][q].format(symbol=_symbol_phrase(label, "[legend image]", True))
    def account(e):
        tokens["calls"] += 1; tokens["input_tokens"] += e["usage"].get("input_tokens") or 0

    pal = None
    if a.mask_palette:
        from mapdig.palette import mask_image
        pal = {x["label"]: x["colours"] for x in json.load(open(a.mask_palette))["entries"]}
    def masked(arr, e):   # the image Jev sees for legend row e (unchanged without --mask-palette)
        return mask_image(arr, pal[e.get("name", e["label"])], a.mask_tol, edges=a.mask_mode == "unmix") if pal else arr

    def legend_png(e, k):
        icon = Image.open(os.path.join(sym_dir, e["crop"])).convert("RGB")
        if pal:
            icon = Image.fromarray(masked(np.asarray(icon), e))
        icon = icon.resize((icon.width * k, icon.height * k), Image.LANCZOS)
        side = max(280, icon.width + 8, icon.height + 8)
        c = Image.new("RGB", (side, side), (255, 255, 255) if pal else land)
        c.paste(icon, ((side - icon.width) // 2, (side - icon.height) // 2))
        return c

    # 2. stage 1 screening
    t0 = time.time()
    k1 = a.screen_k
    screen_img = Image.fromarray(tile).resize((T * k1, T * k1), Image.LANCZOS)
    images["screen_input"] = save(screen_img, "02_screen_input.png")
    screen_png = png(screen_img)
    screening = []
    if a.trace_classes:
        trace["screening"]["tile_image"] = tsave(screen_png, "screen_tile_x2.png")
    for e in entries:
        leg = legend_png(e, k1)
        leg_bytes = png(leg)
        if pal:
            screen_png = png(Image.fromarray(masked(tile, e)).resize((T * k1, T * k1), Image.LANCZOS))
            if e["index"] in (13, 27):
                save(Image.open(io.BytesIO(screen_png)), f"02_screen_masked_{e['index']:02d}.png")
        r = jev.present(screen_png, leg_bytes, e["label"]); account(r)
        p = r["response"]["answers"]["present"]["noul"]
        if a.trace_classes:
            trace["screening"]["calls"].append({
                "label": e["label"], "legend_image": tsave(leg_bytes, f"screen_legend_{e['index']:02d}.png"),
                "prompt_present": prompt_text("present", e["label"]), "request": r["request"],
                "response": r["response"]["answers"], "usage": r["usage"], "cache_key": r["key"]})
        n_true = sum(t["label"] == e["gt_label"] for t in truth)
        screening.append({"label": e["label"], "gt_label": e["gt_label"], "p_present": p, "n_true": n_true,
                          "screened_in": p >= a.screen_threshold or e["label"] in a.force_classes,
                          "forced": e["label"] in a.force_classes and p < a.screen_threshold})
    images["legend_x2_example"] = save(legend_png(entries[min(11, len(entries) - 1)], k1), "03_legend_input_x2.png")
    t_screen = time.time() - t0

    # 3. stage 2 search loop per screened-in class
    S, k2 = a.sub_px, a.sub_k
    subs = [(sx, sy) for sy in list(range(0, T - S + 1, a.sub_step)) for sx in list(range(0, T - S + 1, a.sub_step))]
    preds, loop_log, frames = [], [], []
    t1 = time.time()
    for e, s1 in zip(entries, screening):
        if not s1["screened_in"]:
            continue
        work = masked(tile, e).copy()
        removed = np.zeros((T, T), bool)
        leg_png = png(legend_png(e, k2))
        n_calls_before = tokens["calls"]
        traced = e["label"] in a.trace_classes
        if traced:
            trace["loops"][e["label"]] = {"legend_image": tsave(leg_png, f"loop_legend_{e['index']:02d}.png"),
                                          "prompt_present": prompt_text("present", e["label"]),
                                          "prompt_where": prompt_text("where", e["label"]), "calls": []}
        for (sx, sy) in subs:
            for pas in range(1, a.max_passes + 1):
                sub = Image.fromarray(work[sy:sy + S, sx:sx + S]).resize((S * k2, S * k2), Image.LANCZOS)
                sub_bytes = png(sub)
                r = jev.present_and_where(sub_bytes, leg_png, e["label"]); account(r)
                ans = r["response"]["answers"]
                p, b, conf = ans["present"]["noul"], ans["where"]["box"], ans["where"]["confidence"]
                bx0, bx1 = sx + b["left"] * S, sx + b["right"] * S
                by0, by1 = sy + b["top"] * S, sy + b["bottom"] * S
                ix0, iy0 = max(int(np.floor(bx0)), 0), max(int(np.floor(by0)), 0)
                ix1, iy1 = min(int(np.ceil(bx1)), T), min(int(np.ceil(by1)), T)
                overlap = float(removed[iy0:iy1, ix0:ix1].mean()) if ix1 > ix0 and iy1 > iy0 else 1.0
                step = {"label": e["label"], "sub": [sx, sy], "pass": pas, "p_present": p, "box_conf": conf,
                        "box": [round(bx0, 1), round(by0, 1), round(bx1, 1), round(by1, 1)],
                        "removed_overlap": round(overlap, 2)}
                if p < a.stop_threshold:
                    step["action"] = "stop: not present"
                elif overlap > 0.5:
                    step["action"] = "stop: box on removed area"
                else:
                    step["action"] = "detect + inpaint"
                    cx, cy = (bx0 + bx1) / 2, (by0 + by1) / 2
                    preds.append({"label": e["label"], "gt_label": e["gt_label"], "x": cx, "y": cy,
                                  "box_confidence": conf, "present_prob": p, "pass_index": pas, "sub": [sx, sy]})
                    # frame: enlarged sub-tile with the box, before inpainting
                    fr = sub.copy(); dr = ImageDraw.Draw(fr)
                    dr.rectangle([b["left"] * S * k2, b["top"] * S * k2, b["right"] * S * k2, b["bottom"] * S * k2],
                                 outline="#e0218a", width=6)
                    mask = np.zeros((T, T), np.uint8)
                    mask[max(iy0 - 1, 0):min(iy1 + 1, T), max(ix0 - 1, 0):min(ix1 + 1, T)] = 255
                    work = cv2.inpaint(work, mask, 3, cv2.INPAINT_TELEA)
                    removed |= mask.astype(bool)
                    after = Image.fromarray(work[sy:sy + S, sx:sx + S]).resize((S * k2, S * k2), Image.LANCZOS)
                    n = len(preds)
                    frames.append({"label": e["label"], "sub": [sx, sy], "pass": pas, "p_present": p, "box_conf": conf,
                                   "before": save(fr.resize((400, 400)), f"f{n:03d}_a.png"),
                                   "after": save(after.resize((400, 400)), f"f{n:03d}_b.png")})
                loop_log.append(step)
                if traced:
                    n = len(trace["loops"][e["label"]]["calls"])
                    trace["loops"][e["label"]]["calls"].append({
                        **step, "image": tsave(sub_bytes, f"loop_{e['index']:02d}_{n:03d}.png"),
                        "map_px_origin": [tx + sx, ty + sy], "request": r["request"],
                        "response": ans, "usage": r["usage"], "cache_key": r["key"], "n_pred": len(preds)})
                if step["action"].startswith("stop"):
                    break
        s1["stage2_calls"] = tokens["calls"] - n_calls_before
        s1["detections"] = sum(p_["label"] == e["label"] for p_ in preds)
        Image.fromarray(work).save(os.path.join(img_dir, f"work_{e['index']:02d}.png"))
        s1["work_image"] = f"img/work_{e['index']:02d}.png"
    t_loop = time.time() - t1

    # 4. merge duplicates (same class within 4 px), georeference, GeoPackage
    merged = []
    for p_ in sorted(preds, key=lambda q: -q["present_prob"]):
        if not any(q["gt_label"] == p_["gt_label"] and np.hypot(q["x"] - p_["x"], q["y"] - p_["y"]) <= 4 for q in merged):
            merged.append(p_)
    for p_ in merged:
        mx, my = tf * (tx + p_["x"], ty + p_["y"])
        p_["map_x"], p_["map_y"] = mx, my
    gpkg = os.path.join(a.outdir, "predictions.gpkg")
    if merged:
        geoms = shapely.to_wkb(shapely.points([[p_["map_x"], p_["map_y"]] for p_ in merged]))
        fields = {"class": [p_["gt_label"] for p_ in merged], "legend_label": [p_["label"] for p_ in merged],
                  "source_map": [os.path.basename(os.path.dirname(a.map))] * len(merged),
                  "tile_id": [f"{tx}_{ty}"] * len(merged),
                  "px_x": np.array([tx + p_["x"] for p_ in merged]), "px_y": np.array([ty + p_["y"] for p_ in merged]),
                  "box_confidence": np.array([p_["box_confidence"] or np.nan for p_ in merged], float),
                  "present_prob": np.array([p_["present_prob"] for p_ in merged], float),
                  "pass_index": np.array([p_["pass_index"] for p_ in merged], np.int32),
                  "method": ["jev_loop_two_stage"] * len(merged)}
        fields = {k_: (v if isinstance(v, np.ndarray) else np.array(v, dtype=object)) for k_, v in fields.items()}
        if os.path.exists(gpkg):
            os.remove(gpkg)
        pyogrio.raw.write(gpkg, geoms, list(fields.values()), list(fields.keys()), layer="predictions",
                          driver="GPKG", geometry_type="Point", crs="EPSG:3857")

    # 5. score: one-to-one greedy by distance, same class, <= match px
    pairs = sorted(((np.hypot(p_["x"] - t["x"], p_["y"] - t["y"]), i, j) for i, p_ in enumerate(merged)
                    for j, t in enumerate(truth) if p_["gt_label"] == t["label"]))
    used_p, used_t, tp = set(), set(), []
    for d, i, j in pairs:
        if d <= a.match_px and i not in used_p and j not in used_t:
            used_p.add(i); used_t.add(j); tp.append(d)
    for i, p_ in enumerate(merged):
        p_["match"] = "TP" if i in used_p else "FP"
    for j, t in enumerate(truth):
        t["match"] = "TP" if j in used_t else "FN"
    P = len(tp) / len(merged) if merged else 0.0
    R = len(tp) / len(truth) if truth else 0.0
    F = 2 * P * R / (P + R) if P + R else 0.0
    per_class = {}
    for lab in sorted({t["label"] for t in truth} | {p_["gt_label"] for p_ in merged}):
        per_class[lab] = {"true": sum(t["label"] == lab for t in truth),
                          "pred": sum(p_["gt_label"] == lab for p_ in merged),
                          "tp": sum(p_["gt_label"] == lab and p_["match"] == "TP" for p_ in merged)}

    # result image: tile x2, truth (circles) and predictions (crosses)
    k = 2
    res = Image.fromarray(tile).resize((T * k, T * k), Image.LANCZOS); dr = ImageDraw.Draw(res)
    col = {"TP": "#1a9e3f", "FP": "#e0218a", "FN": "#f08c00"}
    for t in truth:
        if t["match"] == "FN":
            dr.ellipse([t["x"] * k - 12, t["y"] * k - 12, t["x"] * k + 12, t["y"] * k + 12], outline=col["FN"], width=3)
    for p_ in merged:
        x, y = p_["x"] * k, p_["y"] * k
        dr.line([x - 10, y - 10, x + 10, y + 10], fill=col[p_["match"]], width=4)
        dr.line([x - 10, y + 10, x + 10, y - 10], fill=col[p_["match"]], width=4)
    images["result"] = save(res, "09_result.png")

    jev_cost = tokens["input_tokens"] * JEV_PRICE
    report = {
        "tile": {"x": tx, "y": ty, "px": T, "map": a.map, "metres_per_px_web_mercator": abs(tf.a),
                 "ground_m_approx": round(T * abs(tf.a) * 0.669), "classes_present": len({t["label"] for t in truth}),
                 "icons_present": len(truth)},
        "settings": {k_: v for k_, v in vars(a).items() if k_ not in ("stage",)},
        "legend": sym["summary"],
        "screening": screening, "subtiles": len(subs), "loop": loop_log, "frames": frames,
        "predictions": [{k_: v for k_, v in p_.items()} for p_ in merged], "truth": truth,
        "metrics": {"tp": len(tp), "fp": len(merged) - len(tp), "fn": len(truth) - len(tp), "precision": round(P, 3),
                    "recall": round(R, 3), "f1": round(F, 3),
                    "median_err_px": round(float(np.median(tp)), 2) if tp else None,
                    "median_err_m_ground": round(float(np.median(tp)) * abs(tf.a) * 0.669, 2) if tp else None,
                    "per_class": per_class},
        "cost": {"jev_calls": tokens["calls"], "jev_input_tokens": tokens["input_tokens"],
                 "jev_usd": round(jev_cost, 4), "opus_usd": sym["summary"]["cost_usd"],
                 "total_usd": round(jev_cost + sym["summary"]["cost_usd"], 4),
                 "api_new_calls": cache.calls, "api_cache_hits": cache.hits},
        "timing_s": {"screening": round(t_screen, 1), "search_loop": round(t_loop, 1)},
        "images": images,
    }
    json.dump(report, open(os.path.join(a.outdir, "report.json"), "w"), indent=1, default=float)
    if a.trace_classes:
        for lab, L in trace["loops"].items():   # attach the final verdict of each detection
            for c in L["calls"]:
                if c["action"].startswith("detect"):
                    p_ = preds[c["n_pred"] - 1]
                    hit = next((q for q in merged if q is p_), None)
                    c["verdict"] = hit["match"] if hit else "merged duplicate"
                    near = sorted((float(np.hypot(p_["x"] - t["x"], p_["y"] - t["y"])), t["label"]) for t in truth)
                    c["nearest_truth"] = {"label": near[0][1], "dist_px": round(near[0][0], 1)} if near else None
        trace["truth_in_tile"] = {lab: [t for t in truth if t["label"] == lab] for lab in trace["loops"]}
        trace["missed"] = {lab: [t for t in truth if t["label"] == lab and t["match"] == "FN"] for lab in trace["loops"]}
        trace["tile"] = {"x": tx, "y": ty, "px": T, "sub_px": S, "sub_k": k2, "screen_k": k1}
        json.dump(trace, open(os.path.join(a.outdir, "trace.json"), "w"), indent=1, default=float)
    m_.extra.update({"metrics": report["metrics"], "cost": report["cost"]})
    m_.write(os.path.join(a.outdir, "manifest.json"), outputs=["report.json", "predictions.gpkg", "img/"])
    print(json.dumps({"tile": report["tile"], "metrics": {k_: v for k_, v in report["metrics"].items() if k_ != "per_class"},
                      "cost": report["cost"], "timing_s": report["timing_s"]}, indent=1))
