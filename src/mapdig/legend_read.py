"""Stage `read-legend`: Claude Opus reads the legend sheet; code crops the symbols.

Opus returns each entry's label and the pixel box of its symbol (structured JSON output).
The crop is then tightened in code to the non-background pixels inside that box: the
symbol is cut from the legend image, never regenerated. Each read box is also scored
(IoU) against the true legend boxes, and every crop is assigned the ground-truth class
whose true box it overlaps most (used for evaluation only; detection uses Opus's label).
Writes into --outdir: symbols.json, crops/<nn>.png, read_overlay.png, manifest.json.
"""
import base64, io, json, os, re

MODEL = "claude-opus-5-5"
PRICE_IN, PRICE_OUT = 4.00e-6, 20.00e-6   # $/token, Claude Opus 5.5 (skill table, cached 2026-11-03)
PROMPT_VERSION = "v1"
PROMPT = (
    "This image is the legend of a map. For every legend entry, return its label text exactly as "
    "printed and the bounding box of its symbol only (not the label text), in pixel coordinates of "
    "this image: [x0, y0, x1, y1] with x to the right and y down, tight around the drawn symbol. "
    "The image is {w}x{h} pixels. Do not include the legend title."
)
SCHEMA = {
    "type": "object",
    "properties": {"entries": {"type": "array", "items": {
        "type": "object",
        "properties": {"label": {"type": "string"},
                       "box": {"type": "array", "items": {"type": "number"}}},
        "required": ["label", "box"], "additionalProperties": False}}},
    "required": ["entries"], "additionalProperties": False,
}

def add_args(p):
    p.add_argument("--sheet", required=True)
    p.add_argument("--legend-gt", required=True, help="true boxes, for scoring and class assignment only")
    p.add_argument("--upscale", type=int, default=3, help="enlarge the sheet before sending (boxes mapped back)")
    p.add_argument("--cache", default="cache/api")
    p.add_argument("--api-mode", default="online", choices=["online", "offline", "refresh"])
    p.add_argument("--outdir", required=True)

def _iou(a, b):
    ix = max(0, min(a[2], b[2]) - max(a[0], b[0])); iy = max(0, min(a[3], b[3]) - max(a[1], b[1]))
    inter = ix * iy
    u = (a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - inter
    return inter / u if u > 0 else 0.0

def run(a):
    import numpy as np
    from PIL import Image, ImageDraw
    from mapdig.apicache import ApiCache, sha256_bytes
    from mapdig.manifest import Manifest

    m_ = Manifest("read-legend", {"model": MODEL, "prompt_version": PROMPT_VERSION, "upscale": a.upscale},
                  inputs=[a.sheet, a.legend_gt])
    os.makedirs(os.path.join(a.outdir, "crops"), exist_ok=True)
    sheet = Image.open(a.sheet).convert("RGB")
    big = sheet.resize((sheet.width * a.upscale, sheet.height * a.upscale), Image.LANCZOS)
    buf = io.BytesIO(); big.save(buf, "PNG"); png = buf.getvalue()
    prompt = PROMPT.format(w=big.width, h=big.height)
    request = {"model": MODEL, "prompt_version": PROMPT_VERSION, "prompt": prompt, "schema": SCHEMA,
               "image_sha256": sha256_bytes(png), "effort": "high", "fallbacks": "default"}

    def call():
        import anthropic
        client = anthropic.Anthropic()
        r = client.beta.messages.create(
            model=MODEL, max_tokens=16000,
            betas=["server-side-fallback-2026-07-01"], fallbacks="default",
            output_config={"effort": "high", "format": {"type": "json_schema", "schema": SCHEMA}},
            messages=[{"role": "user", "content": [
                {"type": "image", "source": {"type": "base64", "media_type": "image/png",
                                             "data": base64.standard_b64encode(png).decode()}},
                {"type": "text", "text": prompt}]}])
        if r.stop_reason == "refusal":
            raise SystemExit(f"Opus refused: {r.stop_details}")
        text = next(b.text for b in r.content if b.type == "text")
        u = r.usage
        return ({"model": r.model, "stop_reason": r.stop_reason, "entries": json.loads(text)["entries"]},
                {"input_tokens": u.input_tokens, "output_tokens": u.output_tokens})

    entry = ApiCache(a.cache, a.api_mode).get_or_call("anthropic", request, call)
    usage = entry["usage"]
    cost = usage["input_tokens"] * PRICE_IN + usage["output_tokens"] * PRICE_OUT

    gt = json.load(open(a.legend_gt))["items"]
    arr = np.asarray(sheet).astype(int)
    land = arr[2, 2]
    fg = np.abs(arr - land).max(axis=2) > 8
    out, overlay = [], sheet.resize((sheet.width * 2, sheet.height * 2), Image.NEAREST)
    d = ImageDraw.Draw(overlay)
    for i, e in enumerate(entry["response"]["entries"]):
        bx = [v / a.upscale for v in e["box"]]
        x0, y0, x1, y1 = (int(np.floor(bx[0])) - 2, int(np.floor(bx[1])) - 2,
                          int(np.ceil(bx[2])) + 2, int(np.ceil(bx[3])) + 2)
        x0, y0 = max(x0, 0), max(y0, 0)
        ys, xs = np.nonzero(fg[y0:y1, x0:x1])
        refined = ([int(xs.min()) + x0, int(ys.min()) + y0, int(xs.max()) + x0 + 1, int(ys.max()) + y0 + 1]
                   if len(xs) else None)
        best = max(gt, key=lambda g: _iou(refined or bx, g["box"]))
        iou_read, iou_ref = _iou(bx, best["box"]), _iou(refined, best["box"]) if refined else 0.0
        slug = re.sub(r"[^a-z0-9]+", "_", e["label"].lower()).strip("_")
        crop_path = os.path.join("crops", f"{i:02d}_{slug}.png")
        if refined:
            sheet.crop(tuple(refined)).save(os.path.join(a.outdir, crop_path))
        out.append({"index": i, "label": e["label"], "read_box": [round(v, 1) for v in bx], "crop_box": refined,
                    "crop": crop_path if refined else None, "gt_label": best["label"], "gt_file": best["file"],
                    "gt_box": best["box"], "iou_read": round(iou_read, 3), "iou_crop": round(iou_ref, 3),
                    "label_exact": e["label"].strip().lower() == best["label"].strip().lower()})
        d.rectangle([v * 2 for v in bx], outline="#e0218a", width=2)
        if refined:
            d.rectangle([v * 2 for v in refined], outline="#1a9e3f", width=1)
    overlay.save(os.path.join(a.outdir, "read_overlay.png"))
    summary = {"model": entry["response"]["model"], "entries_read": len(out), "entries_true": len(gt),
               "classes_covered": len({o["gt_label"] for o in out if o["iou_crop"] > 0.5}),
               "labels_exact": sum(o["label_exact"] for o in out),
               "median_iou_read": float(np.median([o["iou_read"] for o in out])) if out else 0,
               "median_iou_crop": float(np.median([o["iou_crop"] for o in out])) if out else 0,
               "input_tokens": usage["input_tokens"], "output_tokens": usage["output_tokens"],
               "cost_usd": round(cost, 4), "latency_s": entry.get("latency_s"), "cache_key": entry["key"]}
    json.dump({"summary": summary, "entries": out}, open(os.path.join(a.outdir, "symbols.json"), "w"), indent=1)
    m_.extra.update(summary)
    m_.write(os.path.join(a.outdir, "manifest.json"), outputs=["symbols.json", "crops/", "read_overlay.png"])
    print(json.dumps(summary, indent=1))
