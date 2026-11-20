# Map digitizer: design

Agreed 2026-11-19. Background reading: [research/map-digitization-ai-literature.md](research/map-digitization-ai-literature.md).

## Research claim

Legend-only, no-per-map-training point-symbol detection with TypeSafe **Jev**, compared against detectors trained on each map series. Accuracy and cost per map are secondary results.

- **Scope:** point symbols only. Areas, lines and text are future work.
- **Phases:** (1) OpenStreetMap renders, (2) cleaner digital topographic maps, (3) scans of printed maps. Inputs are always already georeferenced.

## Phase 1 data: OpenStreetMap

| Item | Decision |
|---|---|
| Source | Geofabrik extract `europe/germany/baden-wuerttemberg/freiburg-regbez`. The snapshot timestamp is in `data/extract-info.txt` (2026-11-18T21:21:02Z). |
| Rendering | Local Docker stack (`docker-compose.yml`): PostGIS + Mapnik + openstreetmap-carto **v5.9.0**. Output is GeoTIFF in EPSG:3857, snapped to the web-map pixel grid. The osm.org tile servers are not used (bulk download is against the tile usage policy). |
| Main setting | Zoom 17, scale 1. That is 1.194 Web-Mercator m/px, which is **about 0.80 m/px on the ground at 48°N**. Icons are 6–14 px. |
| Ablations | Zoom 16 and 18. Sharp Mapnik `--scale 2` (best case). |
| Classes | 25 icon classes, defined by icon file, listed in `config/osm_classes.csv` and grouped by icon colour (brown 7, blue 8, red 3, green 3, 4 others). Chosen from `scripts/count_classes.py`. At z17, openstreetmap-carto draws restaurants, cafés, bars and most shops as **4 px colour dots**, not icons. They become icons only at z18, so they are excluded at z17. |
| Areas | Freiburg city centre (dense) plus a rural Black Forest area (sparse). Split into spatial blocks: train (YOLOv8/YOLSO), val (thresholds, calibration), test (all methods). |
| Ground truth | **Render diff.** Render once normally, then once per class with that class's markers set to opacity 0. Opacity 0 keeps collision and placement unchanged. Each changed connected component is one drawn icon. Components that merged across touching icons are split using the icon size from the legend ground truth. This records what was *drawn* (after collision dropping and area-icon placement), not what is in the database. Implemented in `scripts/gt_render_diff.py`. **Renders are only deterministic with PostgreSQL parallel query off** (`max_parallel_workers_per_gather=0`, set in compose). With it on, row order changes collision and two renders of the same style differ by thousands of pixels. |
| Legend | `scripts/legend_sheet.py` draws each icon with the style's own z17 MarkersSymbolizer (same SVG, colour and size) on the land colour, with labels. It writes the sheet, the true icon boxes (to score the VLM's legend reading) and perfect crops (the control). Known gap: some classes use the same icon in a second colour (e.g. pale-blue private Parking), which the legend does not show. |

## Pipeline

1. **Legend reading:** **Claude Opus 5.5** (`claude-opus-5-5`) gets the legend sheet and returns `[{label, box}]` as JSON. Code crops each symbol. Nothing is regenerated.
2. **Tiling:** tiles of about 512–768 px, with overlap of at least 2× the largest symbol.
3. **Enlarging:** tile and legend symbol are enlarged by the same factor k ∈ {1, 2, 3, 4} (Lanczos). This is the main lever, because it is the only one available for scans. Results are scaled back to original pixels before georeferencing. Record each symbol's size in pixels.
4. **Legend crop sizing:** pad the crop (in its own background colour) to Jev's 280 px minimum. Never stretch it on its own.
5. **Jev input:** the legend-symbol image plus its label, e.g. "the 'pharmacy' symbol shown here". Image-only runs as an ablation.
6. **Method A, search loop (main method):**
   1. Per class and tile, ask a Noul: "is there an unmasked instance?"
   2. Ask a Box question for its location.
   3. Remove the boxed area by **inpainting** (`cv2.inpaint`) and repeat.
   4. Stop when any of these holds: P(yes) < threshold (tuned on val); the box mostly overlaps already-removed area; the box repeats the previous one; N passes are reached.
7. **Method B, propose then verify:** template matching proposes candidates, and Jev answers a yes/no per candidate crop.
8. **Removal ablations:** inpaint (default), blur, median-background fill, solid black.
9. **Merging:** merge duplicates across tile overlaps by distance. Convert pixels to map coordinates with the GeoTIFF transform.

## Output: GeoPackage points

Fields: `class`, `legend_label`, `source_map`, `tile_id`, `px_x`, `px_y`, `box_confidence`, `present_prob`, `pass_index`, `score_calibrated` (isotonic fit on val), `method`, `run_id`.

## Baselines

1. Template matching (multi-scale, OpenCV), as a floor.
2. YOLOv8, trained on the train blocks.
3. YOLSO (centre + class), trained on the train blocks.
4. A legend-prompted method: Saxton 2024 or DIGMAPPER's point module if their code runs. Otherwise their published AI4CMA numbers, clearly marked as not re-run.

Hardware: RTX 3060 Ti 8 GB.

## Evaluation

- One-to-one matching of each prediction to an unmatched ground-truth point of the same class within **7 px** (half an icon, about 5.6 m on the ground at z17 and 48°N).
- Per-class and overall precision, recall and F1.
- An F1 curve over 2–20 px.
- Median error in metres for correct hits.
- API calls and cost per km².
- An additional finding: how much a naive database-derived ground truth overstates misses.

## Reproducibility

- Pin `jev-1.14.0` (Box requires the `TypeSafe-Danger-Zone-Images: true` header) and the Opus model version.
- Cache every API request and response on disk.
- Report the run dates and the extract timestamp.
- Phases 2 and 3: check the licence of each map before sending it to hosted APIs.

## Jev constraints (from docs.typesafe.ai, checked 2026-11-19)

- Images must be 280–1568 px per side. Images outside this range are rejected, not resized.
- A Box question always returns exactly one box, with no "not found" answer. Box is experimental.
- "Does not count reliably". There is no documented coordinate precision. Small targets in large images can be missed.
- Hosted only, no fine-tuning. Roughly $0.042 per million input tokens, with images billed as input.
