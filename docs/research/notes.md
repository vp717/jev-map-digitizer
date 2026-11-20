# Research notes

A running lab notebook for the map-digitizer project: findings, numbers, surprises and open questions as they happen. The newest entries are at the top. Each entry points to the evidence: commit, output file, cache or log. Design decisions live in [../design.md](../design.md) and [../pipeline-spec.md](../pipeline-spec.md). This file records *what we observed*.

---

## 2026-11-20: Jev localisation pilot: how big must an icon be?

**Question.** Can Jev's Box question place a small legend symbol on an OSM render? At what on-screen icon size does it become reliable?

**Setup.**
- Stage `pilot-jev`, commit `c61f780`.
- Outputs: `out/osm_phase1/pilot_jev/{calls,summary}.csv`. Responses are in `cache/api/typesafe/`.
- Data: Freiburg centre, z17, scale 1. Native icons are 6–14 px; the classes tested are about 12–14 px.
- Classes: Doctor (red), Parking (blue "P"), Church (black cross).
- One Jev call per tile, `jev-1.14.0`, prompt `v1`, with two questions: Noul "present?" and Box "where?".
- The legend symbol is enlarged by the same k as the tile, then padded to 280 px.
- Per class and setup: 10 tiles that contain the class (an instance placed at a random offset) and 5 random tiles without it. Seed 17.

**Results** (ranges across the three classes):

| Map px per tile × k | Image sent | Icon size as seen by Jev | Icon as % of image width | Box contains an icon | Box centre ≤ 7 map px from an icon | Median centre error (map px) |
|---|---|---|---|---|---|---|
| 640 × 2 | 1280 px | ~28 px | ~2.2% | 50–80% | 20–40% | 7.5–20.9 |
| 320 × 4 | 1280 px | ~56 px | ~4.4% | 70–90% | 50–90% | 2.8–6.8 |
| 160 × 8 | 1280 px | ~112 px | ~8.8% | **100%** | **80–100%** | **1.2–2.0** |

**Findings.**
1. **Minimum icon size for reliable localisation: about 100 px as seen by Jev (about 9% of the image width).** At about 112 px the box centre falls within 1–2 map px of the true icon. That is far inside the 7 px (about 5.6 m) matching rule. Box sizes (11–14 map px) also match the real icon size. At about 56 px the results are mixed. At about 28 px the box is usually wrong: for example, a 288 × 51 px box with confidence 0.05 that contained none of the 8 Doctors in the tile.
2. **"Is it present?" works at every magnification, but "where is it?" does not.** The Noul separated tiles with and without the class perfectly (AUC 1.0) in all 9 class × setup cells, even at 640 × 2. There, mean P(present) was 0.76–0.95 on tiles with the class and 0.07–0.20 on tiles without it. Jev can tell a small symbol is there well before it can box it. **Implication:** a cheap presence check on large tiles, then Box on small enlarged sub-tiles (two-stage search).
3. **Cost per call is constant: about 5,080 input tokens**, regardless of tile area, magnification or class. Output tokens are about 36. Latency is about 0.8 s. So cost scales with the number of calls, not image content: about $0.0002 per call at $0.042 per million input tokens.

**Caveats.**
- Small samples (10 + 5 per cell). These are directional results, not paper numbers.
- The tiles without the class were random tiles. Tiles with look-alike icons were not tested, so the presence AUC is optimistic.
- Single calls only. The search loop (inpaint, repeat, stop) is untested.
- Only 3 of the 25 classes.

**Confound to resolve.** The image size was 1280 px in every setup, so three things changed together: the icon's absolute size in the image, the icon's fraction of the image, and how much map context the tile shows. We do not yet know which one Jev actually needs. **Planned ablation:**
- Same k, different image sizes: e.g. 160 × 4 (a 640 px image with ~56 px icons at 8.8% of the width) against 320 × 4 (a 1280 px image with ~56 px icons at 4.4%).
- Same icon fraction, different absolute sizes: e.g. 80 × 8 against 160 × 8. This needs ≥ 280 px images, so 80 × 4 = 320 px against 160 × 4.

This matters for scans (phase 3). If absolute size is what counts, low-resolution scans need enlarging. If the fraction is what counts, small tiles alone may be enough.

**Cost implication** (exhaustive search, 25 classes, 160 px tiles, 128 px step):
- 43.7 km² (Freiburg 10.3 km² + Hinterzarten 33.4 km²) → 4,233 tiles → about 105,800 first-pass calls → **about $23, or about $0.52 per km²**.
- A 1:25k sheet (about 130 km²) would cost about $65.
- The rural area is 76% of the calls but only 16% of the icons (257 of 1,638). This motivates the two-stage search.

---

## 2026-11-20: TypeSafe SDK facts (typesafe-sdk 0.7.5, read from installed source)

- `TypeSafeClient(model=..., headers=...)`, `client.system_one(state, questions, model=..., assets=...)`.
- Images: `Image(bytes|path)`. Put the image directly in `state` (e.g. `{"map": Image(...)}`), or reference it inside question text via `with client.attach_assets(img): ... f"... {img} ..."`. `str(img)` is a `<image:hex>` reference.
- `BoxAnswer.box` = `{top, bottom, left, right}` as fractions of the image, plus `confidence` (0–1 or None). `NoulAnswer.noul` = P(yes). `response.usage` = `{input_tokens, output_tokens}`.
- Images and Box need the header `TypeSafe-Danger-Zone-Images: true`, and Box needs `jev-1.14.0`. Images must be 280–1568 px per side (docs.typesafe.ai).

---

## 2026-11-20: Pipeline reproducibility checks

- A Snakemake run reproduced the earlier hand-run renders and ground truth **pixel- and point-identically** for both areas (1,381 and 257 icons). Commit `53bdd65`.
- The API cache makes paid stages free to replay: re-running the pilot from committed code gave 135 cache hits and 0 calls. The manifest is clean (`dirty: false`).

---

## 2026-11-19: OSM rendering and ground-truth findings

1. **Renders are non-deterministic unless PostgreSQL parallel query is off.** Two renders of the same style differed by about 2,200–5,400 pixels, because rows arrive in a different order, which changes label and icon collision. With `max_parallel_workers_per_gather=0` the renders are identical. This is essential for render-diff ground truth, and worth a sentence in the paper's methods.
2. **Collision dropping is large in dense areas.** In Freiburg centre at z17, the counts drawn against the candidates from the database (before collision) were:
   - Memorial: 189 of 506 (63% dropped, mostly Stolpersteine).
   - Doctor: 96 of 124.
   - Guest house: 2 of 12.

   Ground truth taken straight from the database would count many correct "misses" as errors. Planned side result: quantify that overstatement.
3. **At z17, openstreetmap-carto draws restaurants, cafés, bars and most shops as 4 px colour dots, not icons.** They become icons only at z18 (e.g. café 153, clothes 139 in the study areas). So z17 classes exclude them. Possible z18 extension.
4. **The same icon can appear in two colours.** Parking also appears pale blue (private access) with the same SVG. Ground truth counts both as Parking, but the legend only shows dark blue. This is a realistic legend–map mismatch and will affect Parking results.
5. **Touching icons merge in the render diff.** For example, 19 merged components for Traffic signals in Freiburg, and stacked Parking pairs. They are split using the legend icon size; 0 remain suspect after splitting.
6. **One openstreetmap-carto SVG uses `<clip-path>`, which Mapnik does not support.** It is not yet confirmed whether any of the 25 classes is affected.
7. **Ground resolution.** z17 at 48°N is about 0.80 m/px on the ground (1.194 m/px in Web Mercator), so the 7 px matching distance is about 5.6 m.

## 2026-11-19: Data provenance

- Geofabrik moved the extract into a sub-folder (`.../freiburg-regbez/freiburg-regbez-latest.osm.pbf`; the old URL returns a 308 redirect). It no longer publishes `.md5` files for it.
- The snapshot is pinned by our own md5 `68650c43…` and the OSM replication timestamp **2026-11-18T21:21:02Z**. The "latest" file changes daily, so the `.pbf` must be archived with the paper.
- openstreetmap-carto's `get-fonts.sh` fails (the Noto Emoji zip is invalid), so we use Ubuntu's Noto packages instead. Noto Emoji is missing, which only affects emoji in labels.
