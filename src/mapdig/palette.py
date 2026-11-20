"""Stages `read-palette` and `palette-check` (change 8): colour-mask the map to each symbol's palette.

read-palette: Claude Opus sees every legend crop (enlarged, nearest-neighbour so colours are
exact) and returns, per entry, the minimal set of colours (hex) needed to draw the symbol,
excluding the background. Scored against the style's true fill colour (evaluation only).

mask_image(): keep pixels within --tol (CIE76 delta E, Lab) of any palette colour, set the rest
to white.

palette-check (no Jev calls): for each tolerance, per class, how much of each true icon
survives the mask (kept pixels in the icon's box relative to the masked legend symbol) and how
much of the map is left after masking.
"""
import base64, io, json, os

MODEL = "claude-opus-5-5"
PRICE_IN, PRICE_OUT = 4.00e-6, 20.00e-6
PROMPT_VERSION = "v1"
PROMPT = (
    "Each image above is one symbol cut from a map legend, enlarged with nearest-neighbour "
    "resampling, so every pixel colour is exactly as printed. For each entry, list the smallest set "
    "of colours (as #rrggbb hex) needed to draw the symbol itself, so that someone keeping only "
    "pixels close to these colours would still see the whole symbol. Do not include the plain "
    "background around the symbol. Also give the background colour once."
)
SCHEMA = {"type": "object", "properties": {
    "background": {"type": "string"},
    "entries": {"type": "array", "items": {"type": "object", "properties": {
        "entry": {"type": "integer"}, "colours": {"type": "array", "items": {"type": "string"}}},
        "required": ["entry", "colours"], "additionalProperties": False}}},
    "required": ["background", "entries"], "additionalProperties": False}

def hex_rgb(h):
    h = h.strip().lstrip("#"); return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))

def to_lab(rgb):
    import cv2, numpy as np
    a = np.asarray(rgb, np.float32).reshape(-1, 1, 3) / 255.0
    return cv2.cvtColor(a, cv2.COLOR_RGB2LAB).reshape(np.asarray(rgb).shape[:-1] + (3,))

FILL = "#ffffff"   # masked-out pixels are painted this colour

def effective_palette(colours, tol, fill=FILL):
    """Palette colours that need keeping: those within tol of the fill colour look the same once
    masked, so keeping them would only let background of that colour through."""
    import numpy as np
    f = to_lab(np.array([hex_rgb(fill)], np.uint8))[0]
    return [c for c in colours if np.linalg.norm(to_lab(np.array([hex_rgb(c)], np.uint8))[0] - f) > tol]

def keep_mask(rgb, colours, tol):
    import numpy as np
    colours = effective_palette(colours, tol)
    if not colours:
        return np.zeros(np.asarray(rgb).shape[:-1], bool)
    lab = to_lab(rgb); pal = to_lab(np.array([hex_rgb(c) for c in colours], np.uint8))
    d = np.min(np.linalg.norm(lab[..., None, :] - pal.reshape((1,) * (lab.ndim - 1) + (len(colours), 3)), axis=-1), axis=-1)
    return d <= tol

def unmix_mask(rgb, colours, tol, seg=18.0, amin=0.2, grow=2, bg_win=15):
    """keep_mask plus anti-aliased edge pixels: a pixel that is a blend of a palette colour and the
    local background (median filter, bg_win px) with >= amin palette share, within seg (RGB units)
    of that blend line, and touching the core within `grow` px."""
    import cv2, numpy as np
    rgb = np.ascontiguousarray(rgb, np.uint8)
    core = keep_mask(rgb, colours, tol)
    cols = effective_palette(colours, tol)
    if not cols:
        return core
    pad = bg_win // 2 + 1
    big = cv2.copyMakeBorder(rgb, pad, pad, pad, pad, cv2.BORDER_REPLICATE)
    bg = cv2.medianBlur(big, bg_win)[pad:-pad, pad:-pad].astype(float); p = rgb.astype(float)
    edge = np.zeros(core.shape, bool)
    for c in cols:
        v = np.array(hex_rgb(c), float) - bg; vv = (v * v).sum(-1) + 1e-6
        a = np.clip(((p - bg) * v).sum(-1) / vv, 0, 1)
        resid = np.linalg.norm(p - (bg + a[..., None] * v), axis=-1)
        edge |= (a >= amin) & (resid <= seg) & (np.sqrt(vv) > 40)
    m = core.copy()
    for _ in range(grow):
        m |= (cv2.dilate(m.astype(np.uint8), np.ones((3, 3), np.uint8)) > 0) & edge
    return m

def mask_image(rgb, colours, tol, edges=True):
    import numpy as np
    keep = unmix_mask(rgb, colours, tol) if edges else keep_mask(rgb, colours, tol)
    out = np.array(rgb, copy=True); out[~keep] = 255; return out

# ------------------------------------------------------------------ read-palette
def add_args_read(p):
    p.add_argument("--symbols", required=True)
    p.add_argument("--legend-gt", required=True, help="true symbolizers, for scoring only")
    p.add_argument("--cache", default="cache/api")
    p.add_argument("--api-mode", default="online", choices=["online", "offline", "refresh"])
    p.add_argument("--out", required=True)

def run_read(a):
    import numpy as np
    from PIL import Image
    from mapdig.apicache import ApiCache, sha256_bytes
    from mapdig.manifest import Manifest
    m_ = Manifest("read-palette", {"model": MODEL, "prompt_version": PROMPT_VERSION}, inputs=[a.symbols, a.legend_gt])
    sym = json.load(open(a.symbols)); sdir = os.path.dirname(a.symbols)
    ents = [e for e in sym["entries"] if e["crop"]]
    content, hashes = [], []
    for n, e in enumerate(ents):
        ic = Image.open(os.path.join(sdir, e["crop"])).convert("RGB")
        ic = ic.resize((ic.width * 8, ic.height * 8), Image.NEAREST)
        b = io.BytesIO(); ic.save(b, "PNG"); pb = b.getvalue(); hashes.append(sha256_bytes(pb))
        content += [{"type": "text", "text": f"Entry {n}: {e['label']}"},
                    {"type": "image", "source": {"type": "base64", "media_type": "image/png", "data": base64.standard_b64encode(pb).decode()}}]
    content.append({"type": "text", "text": PROMPT})
    request = {"model": MODEL, "prompt_version": PROMPT_VERSION, "prompt": PROMPT, "schema": SCHEMA,
               "labels": [e["label"] for e in ents], "image_sha256": hashes, "effort": "high", "fallbacks": "default"}
    def call():
        import anthropic
        r = anthropic.Anthropic().beta.messages.create(
            model=MODEL, max_tokens=16000, betas=["server-side-fallback-2026-07-01"], fallbacks="default",
            output_config={"effort": "high", "format": {"type": "json_schema", "schema": SCHEMA}},
            messages=[{"role": "user", "content": content}])
        if r.stop_reason == "refusal":
            raise SystemExit(f"Opus refused: {r.stop_details}")
        text = next(b.text for b in r.content if b.type == "text")
        return ({"model": r.model, "stop_reason": r.stop_reason, **json.loads(text)},
                {"input_tokens": r.usage.input_tokens, "output_tokens": r.usage.output_tokens})
    res = ApiCache(a.cache, a.api_mode).get_or_call("anthropic", request, call)
    cost = res["usage"]["input_tokens"] * PRICE_IN + res["usage"]["output_tokens"] * PRICE_OUT
    gt = {it["label"]: it["symbolizer"] for it in json.load(open(a.legend_gt))["items"]}
    land = np.array(hex_rgb(res["response"]["background"]))
    by_n = {x["entry"]: x["colours"] for x in res["response"]["entries"]}
    out = []
    for n, e in enumerate(ents):
        s = gt.get(e.get("gt_row") or e["gt_label"], {})
        fill = np.array(hex_rgb(s.get("fill", "#000000"))); op = float(s.get("opacity") or 1)
        true = np.round(op * fill + (1 - op) * np.array([242, 239, 233])).astype(int)   # as drawn on the legend's land colour
        cols = by_n.get(n, [])
        de = min(float(np.linalg.norm(to_lab(np.array([hex_rgb(c)], np.uint8))[0] - to_lab(np.array([true], np.uint8))[0])) for c in cols) if cols else None
        out.append({"label": e["label"], "gt_label": e["gt_label"], "colours": cols,
                    "true_fill_as_drawn": "#%02x%02x%02x" % tuple(true), "delta_e_nearest": round(de, 1) if de is not None else None})
    doc = {"background": res["response"]["background"], "entries": out, "cost_usd": round(cost, 4)}
    os.makedirs(os.path.dirname(a.out) or ".", exist_ok=True)
    json.dump(doc, open(a.out, "w"), indent=1)
    m_.extra.update({"cost_usd": doc["cost_usd"]}); m_.write(os.path.splitext(a.out)[0] + "_manifest.json", outputs=[os.path.basename(a.out)])
    for o in out:
        print(f"{o['label']:<36} {o['colours']}  true {o['true_fill_as_drawn']}  dE {o['delta_e_nearest']}")
    print("cost", doc["cost_usd"])

# ------------------------------------------------------------------ palette-check
def add_args_check(p):
    p.add_argument("--map", required=True)
    p.add_argument("--gt", required=True)
    p.add_argument("--symbols", required=True)
    p.add_argument("--palette", required=True)
    p.add_argument("--tile", nargs=2, type=int, required=True)
    p.add_argument("--tols", nargs="+", type=float, default=[5, 10, 15, 20, 30])
    p.add_argument("--outdir", required=True)

def run_check(a):
    import numpy as np, pyogrio, rasterio
    from PIL import Image
    from rasterio.windows import Window
    os.makedirs(a.outdir, exist_ok=True)
    pal = {e["label"]: e for e in json.load(open(a.palette))["entries"]}
    sym = json.load(open(a.symbols)); sdir = os.path.dirname(a.symbols)
    ents = [e for e in sym["entries"] if e["crop"]]
    src = rasterio.open(a.map)
    _, _, _, f = pyogrio.raw.read(a.gt, layer="gt", columns=["label", "px_x", "px_y", "bbox_w", "bbox_h", "appearance"], read_geometry=False)
    lab, gx, gy, bw, bh, app = f[0].astype(str), f[1], f[2], f[3], f[4], f[5].astype(str)
    tx, ty = a.tile; T = 640
    tile = np.moveaxis(src.read((1, 2, 3), window=Window(tx, ty, T, T)), 0, -1)
    res = {}
    for tol in a.tols:
        rows = []
        for e in ents:
            cols = pal[e["label"]]["colours"]
            leg = np.asarray(Image.open(os.path.join(sdir, e["crop"])).convert("RGB"))
            leg_n = int(keep_mask(leg, cols, tol).sum())
            ratios = []
            ga = e.get("gt_appearance") or ""   # score each legend row against icons drawn its way
            same = (app == ga) if ga else np.array(["@" not in x for x in app])
            if not ga and any(x.get("gt_label") == e["gt_label"] and x.get("gt_appearance") and "@" not in x["gt_appearance"] for x in ents):
                same = same & np.array([x not in {y.get("gt_appearance") for y in ents if y["gt_label"] == e["gt_label"]} for x in app])
            for k in np.flatnonzero((lab == e["gt_label"]) & same)[:200]:
                x0, y0 = int(np.floor(gx[k] - bw[k] / 2)), int(np.floor(gy[k] - bh[k] / 2))
                w_, h_ = int(np.ceil(bw[k])) + 1, int(np.ceil(bh[k])) + 1
                win = np.moveaxis(src.read((1, 2, 3), window=Window(x0, y0, w_, h_), boundless=True), 0, -1)
                ratios.append(keep_mask(win, cols, tol).sum() / max(leg_n, 1))
            rows.append({"label": e["label"], "legend_kept_px": leg_n, "n_icons": len(ratios),
                         "icon_kept_median": round(float(np.median(ratios)), 2) if ratios else None,
                         "icons_below_half": int(np.sum(np.array(ratios) < 0.5)) if ratios else 0,
                         "tile_kept_frac": round(float(keep_mask(tile, cols, tol).mean()), 4)})
        res[str(tol)] = rows
    json.dump(res, open(os.path.join(a.outdir, "check.json"), "w"), indent=1)
    for e in ents[:]:
        for tol in a.tols:
            pass
    # previews at the middle tolerance
    mid = a.tols[len(a.tols) // 2]
    Image.fromarray(tile).save(os.path.join(a.outdir, "tile.png"))
    for e in ents:
        Image.fromarray(mask_image(tile, pal[e["label"]]["colours"], mid)).save(os.path.join(a.outdir, f"masked_{e['index']:02d}.png"))
    print("tol  " + "  ".join(f"{e['label'][:14]:>14}" for e in ents[:0]))
    for tol, rows in res.items():
        print(f"== tol {tol}")
        for r in rows:
            print(f"  {r['label']:<36} icon kept median {r['icon_kept_median']}  <0.5: {r['icons_below_half']}/{r['n_icons']}  tile kept {r['tile_kept_frac']:.3%}")
