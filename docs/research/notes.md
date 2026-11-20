# Research notes

A running lab notebook for the map-digitizer project: findings, numbers, surprises and open questions as they happen. The newest entries are at the top. Each entry points to the evidence: commit, output file, cache or log. Design decisions live in [../design.md](../design.md) and [../pipeline-spec.md](../pipeline-spec.md). This file records *what we observed*.

---

## 2026-11-20: Corrected false-positive breakdown (baseline single-tile run)

**Why.** The user noticed run-log cards showing the right icon (Memorial ×3, Doctor ×3 in Jev's answers) marked "false positive". The card layout mixed three different judgements: what the loop claimed, how that claim was scored, and what Jev's Choice said. Checking the cards also showed my earlier categorisation was wrong.

**Rule now used everywhere** (runlog builder `fp_reason`):
- **duplicate:** a true icon of the same class is within 7 px but already matched by another detection.
- **wrong class:** the nearest true icon within 7 px is a different class.
- **off-centre:** the nearest same-class icon is 7–15 px away.
- **nothing nearby:** none of the above.

**Corrected counts (20 false positives):** 8 wrong class, 5 off-centre, 5 nothing nearby, **2 duplicates** (Memorial, Traffic signals). It was not "10 cross-class".

**New issue: duplicates.**
- The demo merges same-class points within only 4 px, which is less than an icon's width (about 12–14 px).
- A first, off-centre box leaves part of the icon un-inpainted, and a later pass finds the remainder about 7 px away.
- **Fix to try:** merge radius ≈ icon size, or a larger inpaint margin when the box is smaller than the legend icon.

The Change 2 conclusion still holds: the Choice check removed all 8 wrong-class false positives.

---

## 2026-11-20: Change 3: tighter crops for the Choice check

**Setup.** Stage `exp-crop`, output in `out/osm_phase1/exp_crop/`. 183 new calls, about $0.05. Same 94 demo-tile detections, same Choice question and 26 options as Change 2; only the crop image changes:
- **wide:** 40 px ×8 (the Change 2 crop).
- **box:** Jev's loop box + 3 px (median 18.5 × 20 px), ×8, padded to 280 px with the land colour.
- **sq20:** 20 px square, ×8, padded to 280 px.

The padding mirrors how the legend options are built, so the icon appears at the same scale in crop and options.

| Crop | Rule | Precision | Recall | F1 | FP removed / 20 | Correct lost |
|---|---|---|---|---|---|---|
| none | – | 0.787 | 0.831 | 0.809 | – | – |
| wide | strict | 0.883 | 0.764 | 0.819 | 11 | 6 |
| **box** | **strict** | **0.908** | **0.775** | **0.836** | 13 | 5 |
| sq20 | strict | 0.918 | 0.753 | 0.827 | 14 | 7 |
| box | gentle | 0.839 | 0.820 | 0.830 | 6 | **1** |

**Findings.**
- Cropping to Jev's own box is best, but the gain is small: +0.017 F1, about two detections, so it is within noise on 94 detections. The cost is the same (about 6,750 tokens per call, dominated by the 25 option images).
- **The Choice answers are noisy.** 17 correct detections were rejected by at least one crop, but rarely by all three. "None of these" answers rise as crops get tighter (7 → 11 → 11). Next idea: a majority vote across crops, or two calls.
- **The surviving false positives are mostly the right class, just off-centre** (8–12 px): Hotel, Charging station, Traffic signals, Memorial. Choice can't fix these. They need re-centring, e.g. template-snapping the point inside Jev's box.
- Both Fitness station "hallucinations" were confirmed by all three crops (wide, box, sq20). That strengthens the case for a real fitness-like icon the ground truth doesn't count. Check by eye.

---

## 2026-11-20: Multi-image calls: batched screening and a Choice check on detections

**Setup.** Stage `exp-multiimage`. Outputs: `out/osm_phase1/exp_multiimage/{summary.json,screening.csv,choice.csv}`. This run made 275 new calls (about $0.07).
- **A. Screening.** 8 non-overlapping 640 px tiles in Freiburg centre (the demo tile plus 7 seeded random ones), 25 classes each, giving 200 class–tile pairs (93 present, 107 absent). Two methods:
  - *single*: 25 calls per tile, one legend excerpt each.
  - *batch*: 1 call per tile with all 25 excerpts attached and 25 Noul questions.
- **B. Choice check.** Each of the demo tile's 94 detections is cropped (40 px, enlarged ×8). Jev picks one option out of 26: the 25 legend excerpts as image options, plus "none of these". A detection is kept only if the pick is its own class.

**A. Batched screening: same overall quality, ~10× cheaper, ~20× faster.**

| | Accuracy @0.5 | AUC | Missed present | False present | Calls | Tokens | Cost | Latency (sequential) |
|---|---|---|---|---|---|---|---|---|
| single | 0.855 | 0.907 | 19/93 | 10/107 | 200 | 963,579 | $0.0405 | 111 s |
| batch | 0.865 | 0.899 | 18/93 | 9/107 | 8 | 93,565 | **$0.0039** | **5.0 s** |

- Agreement at the 0.5 threshold: 97%. Correlation of P: 0.97. Mean |ΔP| = 0.029.
- **Token split** (from the two call shapes): a 1280 px tile costs about 4,530 tokens, and each 280 px legend excerpt about 286 tokens. A batched call is about 11,700 tokens.
- **One severe batch failure.** On tile 6, batch gave **Doctor P = 0.07 against single 0.77, with 9 Doctors present**. Pharmacy also dropped (0.64 to 0.06; it was absent). The other 23 answers on that tile agree, so this is not an answer-ordering bug. Batching can occasionally miss a class that single calls catch, so it needs a larger sample before it replaces single calls.
- **Screening quality in general:** across random tiles, single-call screening misses 19 of 93 present classes (20%). That is far worse than on the dense demo tile, where it missed 2 of 20, and it limits recall upstream of the loop. The threshold and prompt need tuning on validation tiles.

**B. Choice check: precision up, recall down, F1 about the same.**

| | Predictions | Correct | Precision | Recall | F1 |
|---|---|---|---|---|---|
| before | 94 | 74 | 0.787 | 0.831 | 0.809 |
| after Choice | 77 | 68 | **0.883** | 0.764 | 0.819 |

- It removed 11 of 20 false positives:
  - all the look-alike confusions: Statue→Artwork ×3, Statue→Bust, Pharmacy→Doctor, Taxi→Bus stop, Church→Statue;
  - plus 4 that it labelled "none of these".
- It lost 6 correct detections: 4 to "none of these", Traffic signals→Parking, and Artwork→Statue.
- It kept the Fitness station "hallucinations" with P(own) 0.93–0.95. **Open question:** is there really a fitness-like icon there that the ground truth lacks, such as another class using a similar runner symbol? Check visually.
- Cost: 94 calls, about 6,800 tokens each, $0.027, 22 s total. That is about +$0.0003 per detection, so cheap relative to the loop.
- **Better rule to try:** reject only when Jev picks a *different legend class*, and keep the detection when it picks "none of these". That would keep the 4 correct detections lost to "none" and still remove the 7 cross-class false positives.

---

## 2026-11-20: Call-level trace of the single-tile run

**What.** Every call for Doctor, Statue and Parking (92 loop calls), all 25 screening calls and the Opus call were traced. `mapdig demo-tile --trace-classes ... --api-mode offline` writes the exact PNG bytes sent, the prompt text and the raw answers to `out/osm_phase1/demo_tile_trace/`.

**Verification.** The replay ran offline: 569 cache hits, 0 calls. The SHA-256 of every rebuilt image matched its cached request (122 of 122, including the Opus input). So the traced images are exactly what the models saw.

**Observations.**
- **Parking misses are "not present" answers, not bad boxes.** Every sub-tile containing a missed pale-blue Parking icon got P(present) 0.16–0.31 on its first pass. **Hypothesis:** prompt v1 says *"Only count symbols drawn exactly like it (same shape and colour)"*, which tells Jev to reject colour variants. Next, test a prompt without "and colour", or one that names colour variants as the same class, on these sub-tiles. It costs cents and the cache keeps both versions.
- The Doctor sequence shows the loop working as designed: each detection is followed by a call on the inpainted sub-tile that returns "not present".

---

## 2026-11-20: First end-to-end run on one tile (Opus legend + two-stage Jev loop)

**Setup.**
- Stages `read-legend` and `demo-tile`. Outputs: `out/osm_phase1/{legend_read,demo_tile}/`.
- Tile: Freiburg centre, origin (1856, 960) map px, 640 px (about 511 m on the ground). It was chosen automatically as the window with the most classes: 20 classes, 89 icons.
- Legend: Opus 5.5 reads the sheet (enlarged ×3, effort high, structured JSON); code tightens each crop to the icon's non-background pixels.
- Screening: Noul on the tile enlarged ×2, all 25 classes, threshold 0.5.
- Search loop: 160 px sub-tiles (step 120, 25 per tile) enlarged ×8, Noul + Box; stop if P < 0.5 or the box is on an inpainted area; cv2 Telea inpainting of the box (±1 px) in a per-class working copy; at most 8 passes.
- Scoring: one-to-one, same class, ≤ 7 px.

**Legend reading (Opus).**
- All 25 entries found, all 25 labels exact.
- Opus box IoU against the truth: median 0.88 (min about 0.70, Statue).
- After code tightening, all 25 crops equal the true icon boxes pixel for pixel. The Opus-read legend is therefore identical to the perfect control at s1.
- $0.023 (2,751 input / 580 output tokens), 8.9 s.

**Screening (stage 1).**
- 18 of 18 classes present in the tile were screened in.
- The 5 classes absent from the tile were screened out: Viewpoint 0.24, Picnic 0.24, Guest house 0.41, Chalet 0.03, Hospital 0.33.
- 2 present classes were missed: **Bust** (1 icon, P = 0.44) and **Shelter** (1 icon, P = 0.16).
- Screening cost 25 calls, so it is close to free. It did not save much here, because this tile is unusually dense.

**Detection.**

| Precision | Recall | F1 | Median error |
|---|---|---|---|
| 0.787 (74/94) | 0.831 (74/89) | **0.809** | 1.48 px ≈ **1.2 m** |

- Perfect classes: Doctor 8/8, Artwork 4/4, Supermarket 4/4, Bicycle rental 3/3, Museum, Bus stop, Playground and Drinking water.
- Memorial: 20/21 recall, 20/22 precision.

**Error analysis** (20 false positives, 15 misses):
1. **Cross-class confusion is the largest source: 10 of 20 false positives.** *(Corrected later the same day: 8 of 20. The Memorial→Memorial and Traffic signals→Traffic signals cases counted here were duplicates, not cross-class. See the entry "Corrected false-positive breakdown".)* Each class is searched independently, so one icon can be claimed by several look-alike classes:
   - **Statue fired on Artwork ×4 and on Bust ×1.** All three are brown, tall and thin. Statue had 6 predictions for 1 true icon.
   - Pharmacy fired on Doctor ×2 (both red crosses).
   - Taxi rank fired on Bus stop.

   *Fix to try:* resolve conflicts between classes at the same location, by keeping the higher-P class or by asking a Jev Choice among the candidate classes for that crop.
2. **Off by 8–12 px: 5 false positives and about 5 misses are the same icons**, boxed slightly off-centre (Memorial 12 px, Hotel 11 px, Charging station 8 px, Traffic signals 9–12 px). These are probably partial icons at sub-tile edges and boxes spanning two adjacent icons. A 12 px tolerance would turn them into hits, F1 ≈ 0.86. *Fix to try:* re-centre each detection with a crop around the box, or snap to the template.
3. **The pale-blue Parking variant was never found: 3 of 6 Parking icons.** All 3 misses are the light-blue private-parking variant (darkest pixel about RGB 145,187,201), which the legend doesn't show. This confirms the legend–map mismatch predicted on 2026-11-19. It is a realistic failure mode to report.
4. **Dense clusters of Traffic signals: 7 of 18 missed** around junctions where signals sit about 12 px apart. Likely causes: boxes landing between icons, and inpainting of one box clipping its neighbour.
5. **About 5 hallucinations:** Fitness station ×2 (with high box confidence 0.87–0.90), Church ×2, Traffic signals ×1. **Box confidence did not separate these from true hits.**

**Cost and time.**
- 569 Jev calls (25 screening + 544 loop), 2.89 M input tokens, **$0.121**. Opus $0.023. **Total $0.14 for 0.26 km²**, about $0.55/km² in this very dense tile.
- 448 of the 569 calls were "stop: not present" answers, so most of the cost goes on confirming absence.
- Sequential loop time: 188 s (about 0.33 s per call, warm).
- Of the loop steps, 94 detect-and-inpaint, 448 stop on "not present", and 2 stop on "box on removed area".

**Caveats.** One tile, chosen for density, thresholds untuned (0.5 and 0.5). Not a paper result.

---

## 2026-11-20: Coverage per dollar: exhaustive vs two-stage search

**Method.** Call counts estimated from the ground truth, assuming a perfect detector: presence is always right, the loop finds each icon once, and one final "none left" call. Price per call is $0.000213 (about 5,080 tokens × $0.042 per million). All 25 classes.
- **Exhaustive:** 160 px tiles, 128 px step, every class in every tile.
- **Two-stage:** presence check on 640 px tiles (576 px step) for every class, then the Box loop on 160 px sub-tiles (120 px step) only for tile–class pairs that contain the class.

| Area | Icons | Exhaustive | Two-stage | km² per $1 (exh. / two-stage) |
|---|---|---|---|---|
| Freiburg centre, 10.3 km² | 1,381 | 27,120 calls, $5.79 ($0.56/km²) | 15,322 calls, $3.27 ($0.32/km²) | 1.8 / **3.2** |
| Hinterzarten rural, 33.4 km² | 257 | 81,255 calls, $17.34 ($0.52/km²) | 9,111 calls, $1.94 ($0.06/km²) | 1.9 / **17.2** |

**Findings.**
- Exhaustive cost depends on area: about $0.52–0.56/km² whatever is on the map.
- Two-stage cost depends on icon density. It saves about 1.8× in the dense city (459 tile–class pairs need the loop) and about 9× in the rural area (178 pairs). In the city the sub-tile loop dominates (25 sub-tiles per positive pair). A middle stage (320 px) might cut it further.

**Caveats.** False positives in the presence check add sub-tile calls, and missed icons lower the cost but also the recall. The real cost is therefore uncertain until the larger pilot.

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
