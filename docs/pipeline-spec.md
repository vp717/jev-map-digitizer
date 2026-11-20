# Pipeline spec: reproducible runs (DRAFT)

Status: draft 2026-11-20. Items marked **[Q#]** wait on a decision (see the end).

## Goal

Every number, table and figure in the paper can be regenerated from a clean checkout with:
1. API keys, and
2. either live API access or the archived API cache,

by running documented commands. A re-run with unchanged inputs does no work. A re-run with a changed input redoes only the stages downstream of that change.

## Principles

1. **One CLI, one stage per subcommand.** `mapdig <stage> ...` Each stage is a pure function of declared inputs + config → declared outputs. No hidden state, no notebooks in the critical path.
2. **One config file per experiment.** All tunable values live in `config/experiments/<name>.yaml` and nowhere else. Stages read only the keys they declare.
3. **Snakemake runs the grid** (areas × zooms × scales × k × methods × ablations) and skips up-to-date outputs. Each rule's `shell:` calls `mapdig <stage>` inside a container, so every stage can still be run by hand. Config values reach rules via `params:`, so a changed value re-runs only the rules that use it (default `--rerun-triggers`: code input mtime params software-env).
4. **Everything runs in pinned containers.** Images are pinned by digest. Python dependencies are locked.
5. **Hosted models go through a content-addressed cache.** Paper runs can be replayed offline, byte for byte.
6. **Every output carries a manifest:** code commit, image digest, config hash, upstream input hashes, model versions, timings, API cost.

## Config (sketch)

```yaml
# config/experiments/osm_phase1.yaml
name: osm_phase1
data:
  extract_url: https://download.geofabrik.de/europe/germany/baden-wuerttemberg/freiburg-regbez/freiburg-regbez-latest.osm.pbf
  extract_md5: 68650c431104e692143f5fa453ac0afc   # pins the snapshot; fetch fails on mismatch
  style: {name: openstreetmap-carto, version: v5.9.0}
areas:                                             # WGS84 bbox
  freiburg_centre:    [7.825, 47.983, 7.875, 48.008]
  hinterzarten_rural: [8.070, 47.880, 8.160, 47.925]
classes: config/osm_classes.csv
render: {zooms: [17], scales: [1]}
split: {block_m: 500, fractions: {train: 0.6, val: 0.2, test: 0.2}, seed: 17}
tiling: {tile_px: 640, overlap_px: 32, upscale_k: [1, 2, 3, 4], resample: lanczos}
legend_reader: {provider: anthropic, model: claude-opus-5-5}
methods:
  jev_loop:   {model: jev-1.14.0, prompt: image+label, removal: inpaint, max_passes: 8, stop_threshold: from_val}
  jev_verify: {model: jev-1.14.0, proposer: template, proposer_threshold: 0.5}
  template:   {scales: [0.9, 1.0, 1.1], threshold: from_val}
  yolov8:     {weights: yolov8s.pt, imgsz: 640, epochs: 100, seed: 17}
  yolso:      {epochs: 100, seed: 17}
eval: {match_px: 7, curve_px: [2, 20], split: test}
api: {cache: cache/api, mode: online}             # online | offline | refresh
```

## Stages

| # | Stage | Inputs | Outputs (under `out/<experiment>/`) |
|---|---|---|---|
| 1 | `fetch` | extract URL + md5 | `data/<file>.pbf`, `data/extract-info.txt` |
| 2 | `import` | pbf, style version | DB volume + `db/import.json` (pbf md5, style version, osm2pgsql version) |
| 3 | `render` | db stamp, area, z, s | `maps/<area>/z<z>_s<s>/map.tif` |
| 4 | `groundtruth` | db stamp, area, z, s, classes | `maps/<area>/z<z>_s<s>/gt.gpkg`, `gt_summary.csv` |
| 5 | `legend` | classes, z, s | `legend/z<z>_s<s>/{sheet.png, sheet_gt.json, control/}` |
| 6 | `split` | area, gt, split params | `splits/<area>.gpkg` (blocks with train/val/test) |
| 7 | `tiles` | map, split, tiling params, k | `tiles/<area>/z<z>_s<s>/k<k>/manifest.parquet` (windows only; pixels are regenerated deterministically) |
| 8 | `read-legend` | sheet, reader model | `legend_read/<model>/z<z>_s<s>/{symbols.json, crops/}` + score against `sheet_gt.json` |
| 9 | `detect` | tiles, legend (read or control), method params | `runs/<run_id>/predictions.gpkg` (raw, pixel and map coordinates) |
| 10 | `calibrate` | val predictions + gt | `runs/<run_id>/calibration.json`, `predictions_cal.gpkg` |
| 11 | `evaluate` | test predictions + gt | `runs/<run_id>/metrics.json`, `per_class.csv`, `curve.csv` |
| 12 | `train` (YOLOv8, YOLSO) | train/val tiles + gt | `models/<method>/<hash>/weights.pt` (GPU container) |
| 13 | `report` | all metrics | `report/tables/*.csv`, `report/figures/*.pdf` |

`run_id` = `<method>-<short hash of (method params, legend source, area, z, s, k, upstream hashes)>`. The same inputs give the same `run_id`, so finished runs are skipped.

## API cache

- Key: `sha256(provider, model, canonical request JSON incl. image bytes)`. Value: response JSON + timestamp + latency + token usage.
- Modes:
  - `online`: use the cache, call on a miss.
  - `offline`: a miss is an error. Used for paper replays and CI.
  - `refresh`: always call and overwrite.
- Cost: every call logs token usage. `mapdig cost <run_id>` sums it. Each run's manifest records total calls and cost.
- Archiving: the cache for paper runs is frozen and published alongside the paper. **[Q4]**

## Containers

| Image | Contents | Used by |
|---|---|---|
| `render` | Mapnik, osm2pgsql, openstreetmap-carto v5.9.0, GDAL | stages 1–7 |
| `ml` | CUDA, PyTorch, Ultralytics, OpenCV, GDAL | stages 8–13 (GPU for `train` / YOLO / YOLSO inference) |
| `db` | PostGIS 16-3.4, parallel query off | stages 2–4 |

**[Q3]**

## Determinism

- PostgreSQL `max_parallel_workers_per_gather=0` (renders are otherwise not repeatable; already verified).
- Fixed seeds for splits and training. Torch deterministic flags are on where supported, and any remaining non-determinism is documented.
- The extract is pinned by md5. `latest` URLs are only used to fetch; a changed file fails the fetch until the config is updated.
- Tile pixels are regenerated from `map.tif` + window + k, never stored as truth.

## Commands (target surface)

```sh
mapdig run config/experiments/osm_phase1.yaml            # whole grid via the workflow engine
mapdig run config/experiments/osm_phase1.yaml --until groundtruth
mapdig run ... --api-mode offline                        # replay from cache
mapdig <stage> --config ... [--area A --zoom Z --scale S --k K --method M]   # single stage
mapdig status config/experiments/osm_phase1.yaml         # what's done / stale / missing
mapdig cost <run_id>|<experiment>
```

## Open decisions

- ~~[Q1] Workflow engine~~ **Decided 2026-11-20: Snakemake.** See `lessons/0001-what-reruns-when-you-change-something.html` for the comparison.
- CLI name: `mapdig` (accepted 2026-11-20).
- **[Q2]** Packaging of the CLI.
- **[Q3]** Container split.
- **[Q4]** Where large outputs and the API cache live.
- **[Q5]** Version control.
