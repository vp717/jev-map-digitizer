# Conversation summary and critical findings

Covers the working conversation of 19–25 November 2026. Written so the project can be picked up on another
machine without the chat. Detail and evidence: [notes.md](notes.md) (lab notebook),
[run log](../artifacts/runlog/index.html) (one tab per change), [design](../design.md),
[pipeline spec](../pipeline-spec.md), [literature review](map-digitization-ai-literature.md).

## Where things stand

**Goal.** A comparative paper: can TypeSafe Jev (`jev-1.14.0`) find and place point symbols on a map from the
legend alone, with no per-map training, compared with detectors trained on each map series?

**Done.** Reproducible pipeline, exact ground truth, an end-to-end search and eight method changes, almost all
on one dense 640 px OpenStreetMap tile of Freiburg (z17, about 90 icons).

**Best supported result.** F1 about **0.82** (mean of 3 runs, faded icons excluded, 87 icons), with or without
the colour mask. The best single run on all 91 icons scored 0.876 and should not be quoted as the result.

**Not done.** Trained baselines (YOLOv8, YOLSO), template matching, legend-prompted methods, held-out tiles,
threshold tuning, and phases 2–3 (topographic maps, scans). **No comparison claim can be made yet.**

## How it works

1. **Legend:** Claude Opus 5.5 reads the legend sheet (label and box per symbol); code tightens the crops.
2. **Screening:** Jev is asked whether each symbol appears on the 640 px tile (enlarged ×2).
3. **Search loop:** on 160 px sub-tiles (×8) Jev answers "present?" and "where?"; the box is inpainted and the
   question repeated until the answer is no.
4. **Class decision:** Jev picks each detection's symbol from all legend rows plus "none of these".
5. **Scoring:** one-to-one, same class, within 7 px (about 5.6 m). *Strict* keeps a detection only if its own
   class is picked; *gentle* also keeps it on "none".

Ground truth is a render diff: hide one class, render again, and the changed pixels are its icons.

## Critical findings

### 1. Single runs mislead: this qualifies every earlier result

Byte-identical Jev requests give different answers. Repeating the whole search three times:

| Mean of 3 runs | No mask | Colour mask |
|---|---|---|
| Search-loop F1 (range) | 0.784 (0.764–0.816) | **0.811** (0.805–0.817) |
| F1 after the class decision (range) | 0.822 (0.792–0.870) | 0.820 (0.810–0.835) |
| Icons found only in some runs | 10 | **6** |

- One-run, one-tile F1 can move by 0.05 (loop) to 0.08 (class decision). **The Change 2–7 gains that were small
  are not established**, including the 0.841 → 0.876 step.
- The first colour-mask conclusion ("slightly worse") was wrong: the unmasked run it was compared with was the
  best of its three.
- Box centres are stable (median 0.53 px between runs). The noise is in the yes/no answers and class decision.

### 2. On hard icons one answer is right about 3 times in 4, and voting helps

- Ten uncertain medical icons, 30 identical calls each: 77% right with names, 76% with codes. Simulated votes
  of 3 / 5 / 7 calls: about 86 / 92 / 96%. These icons were picked for being hard, so 77% is not Jev's general rate.
- Right answers have median top probability about 1.00; wrong ones about 0.75–0.88. About a quarter of wrong
  answers are still near 1.00.
- **Rule chosen:** keep an answer at 0.95 or above; otherwise vote over 3 calls, then 5 if needed. It recovered 5
  detections for 60 extra calls, against 6 for 384 extra calls when voting on everything.
- **Voting did not remove the 4 wrong points** the strict rule kept. They are consistent mistakes.

### 3. Jev needs big icons

Box is reliable when the icon is about 100 px in the image sent (median error 1.2–2.0 map px at ~112 px). At
~28 px boxes are mostly wrong, though "present?" still works. This motivates the two-stage search. Small pilot;
absolute icon size and share of the image are confounded.

### 4. An incomplete legend looks like hallucination

- Two "hallucinated" Fitness icons were real **Dance** icons missing from our class list. With both symbols
  offered, Jev made 0 Fitness/Dance swaps in 52 questions.
- Per-class loops accept same-colour look-alikes. They are candidate finders; a choice among all symbols should
  assign the class.

### 5. Legends and tags hide variants

- 61% of drawn Parking icons are a faded restricted-access variant the legend omits. Adding a legend row took
  faded Parking from 1 of 4 to 4 of 4 found on the tile.
- Memorial is mostly Stolpersteine; Doctor also covers clinics; Picnic site is mostly the grey table. The
  [icon audit](icon-audit.md) lists every rule.

### 6. Class names seem to bias the search

With names replaced by arbitrary codes, wrong Pharmacy points fell from 11 to 3 (8 medical tiles, loop F1
0.889 → 0.926). For the class decision the result is **unresolved**: 92 vs 101 of 119 icons favours codes, but
on tiles names won (0.930 vs 0.871 gentle), and single-call noise is large. Single runs only.

### 7. The colour mask steadies the search

Opus derives a minimum palette per symbol (one **or more** colours; future maps may differ) and all other pixels
are whited out. White must be dropped from palettes, and blended edge pixels kept, or thin symbols break up.
Screening misses fell from three classes (Bust, Dance venue, Shelter) to one (Shelter) in every run. Same-colour
symbols survive the mask.

### 8. Screening limits recall

On 8 tiles, screening missed 19 of 93 present class–tile pairs. Batching all legend symbols in one call was
about 10× cheaper and 20× faster at similar accuracy, but once missed a class with 9 icons (Doctor, P = 0.07).

### 9. Ground truth must be what was drawn

- Collision handling drops many icons: only 189 of 506 Memorials in the database are drawn. Database truth
  would count these as misses.
- Renders are deterministic only with PostgreSQL parallel query off.

### 10. It is cheap

About $0.14 for the baseline tile. 20 Nov in total: $2.47 for about 9,100 calls. Most loop calls only confirm
absence. Estimated two-stage cost: $0.32/km² (city) and $0.06/km² (rural), assuming a perfect detector.

## Method changes

Single-run results unless marked; differences under about 0.08 F1 may be noise. The truth set also changed:
89 icons up to Change 3, 91 from Change 4, 87 in the noise study.

| Change | Result |
|---|---|
| Baseline | P 0.787, R 0.831, F1 0.809 |
| 1. Batched screening | ~10× cheaper, similar accuracy, one bad miss |
| 2. Class check | Precision 0.787 → 0.883, recall 0.831 → 0.764 (F1 0.819) |
| 3. Tighter crops | Strict F1 0.836 |
| 4. Dance class added | 0 Fitness/Dance swaps; strict F1 0.827 on the new truth |
| 5. Full names, variant rows | Gentle F1 0.846; faded Parking 4 of 4; some Doctor → Pharmacy errors |
| 6. Names vs codes | Codes cut wrong Pharmacy points 11 → 3 |
| 7. Ask again when unsure | Strict F1 0.841 → 0.876 |
| 8. Colour mask (3 runs) | Loop 0.784 → 0.811 and steadier; tie after the class decision |

## Corrections made along the way

- "10 cross-class false positives" was really 8 wrong class, 5 off-centre, 5 nothing nearby, 2 duplicates.
- "Confidence can't be used as a threshold" was wrong: it is a useful trigger to ask again.
- The mask check compared masked icons with a *masked* legend, hiding lost pixels. Compare with the unmasked one.
- Variant legend rows were first scored against every icon of their class; they are now scored by appearance.
- The single-run colour-mask conclusion was reversed (finding 1).

## Decisions and working rules

- Faded restricted-access icons are **on hold**: report results without them; don't tune for them.
- Compare methods as means over at least 3 runs, or more tiles.
- Don't assume one colour per symbol.
- Log each result in `notes.md`; give each method change a run-log tab with exact before and after.
- Commit only as the configured `vp717` identity; never commit `.env`.

## Next steps

1. Several held-out tiles, means over at least 3 runs.
2. Colour mask for screening only, tested on its own.
3. Make "ask again when unsure" the default class decision.
4. Search with codes; confirm with repeat runs.
5. Fix duplicates and off-centre points (merge radius of one icon width, re-centring).
6. Find why the mask lost Memorial and Traffic-signal icons.
7. Baselines, then digital topographic maps and scans.

Open: whether to grey out unused answers on the Change 7 cards (with the adaptive rule, not all 5 count).

## Continuing on another machine

1. Clone the repo and follow the [README](../../README.md). Create `.env` with `TYPESAFE_API_KEY` and
   `ANTHROPIC_API_KEY`.
2. Privately copy `data/` (1.2 GB; Geofabrik's extract changes daily, so the pinned file can't be downloaded
   again) and `cache/` (40 MB). Without `cache/`, calls are paid for again and the numbers will differ. `out/`
   (704 MB) is optional.
3. Rebuild the run log without `--configfile`: passing the v2 config deleted the page and failed.
4. Point a new assistant session at this file, then `notes.md` and the two design documents.
