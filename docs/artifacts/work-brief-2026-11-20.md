# Map digitizer: work brief, 20 Nov 2026

Nov 20, 2026

In one day the project went from an empty repository to a reproducible pipeline in which TypeSafe Jev digitises point symbols from an OpenStreetMap test tile. Averaged over three runs, it reaches F1 0.82: over 90% of its points are real icons, and about three in four icons are found. The best single run scored 0.876, but repeat runs showed that single-run differences of 0.05 to 0.08 are noise. API spend for the day was $2.47 across about 9,100 calls.

## What we built

1. **Test data with exact ground truth.** OpenStreetMap's standard style is rendered from a local copy of the Freiburg extract. Each icon class is hidden in turn and the pixels that change give its exact positions. 26 icon classes.
2. **Legend reading.** Claude Opus 5.5 reads the legend sheet and returns each symbol's label and box. It read all 31 legend rows correctly.
3. **Two-stage Jev search.** Stage 1 asks whether a symbol appears anywhere on the tile. Stage 2 searches enlarged sub-tiles, asks Jev to box each instance, blanks it out and asks again. A final Choice question confirms each point's class.
4. **Reproducibility.** Every step is a Snakemake command in pinned containers. Every API call is cached by content, so any run replays exactly and offline.

## Method changes and results

All on one 640 px test tile with about 90 icons. Each change was compared with the run before it; full before-and-after detail is in the [run log](https://claude.ai/artifact/K8SRvZtk3JX7ZvqWWPYncm).

| Change | What changed | Result |
| --- | --- | --- |
| Baseline | Opus legend + two-stage Jev search | Precision 0.787, recall 0.831, F1 0.809; $0.14 a tile |
| 1. Batched screening | All legend symbols in one stage-1 call | 10× cheaper and 22× faster at similar accuracy, but one class missed badly |
| 2. Class check | Jev picks each point's symbol from the whole legend | Precision 0.787 → 0.883 |
| 3. Tighter crops | Check crop cut to Jev's box + 3 px | F1 0.836, precision 0.908 |
| 4. Dance class | Added the missing Dance icon | The Fitness "hallucinations" were Dance icons; Jev never confused the two once both were offered |
| 5. Full names, variants | Names cover every tag; legend rows for faded and grey variants | Faded Parking found 4 of 4, up from 1 of 4; F1 0.846 |
| 6. Names vs codes | Legend names replaced by arbitrary codes | Names mislead the search: wrong Pharmacy points 11 → 3 with codes |
| 7. Ask again when unsure | Repeat the class check when confidence < 0.95 | F1 0.841 → 0.876 for 60 extra calls |
| 8. Colour mask | Search images masked to each symbol's palette | Search F1 0.784 → 0.811 and far steadier (mean of 3 runs); ties after the class check (0.822 vs 0.820) |

## What we learned about Jev

- **Icons must be big.** Jev boxes an icon reliably only when it spans about 100 px, so map tiles are enlarged 8× before the search.
- **It is not deterministic.** The same request gets the right class about 3 times in 4 on hard icons. A low-confidence answer is usually wrong, so asking again only then fixes most errors cheaply.
- **Box placement is stable; yes/no answers are not.** Box centres move about half a pixel between runs. The variation comes from the presence questions and the class check.
- **One run on one tile misleads.** Repeat runs swung F1 by up to 0.08, which reversed the first colour-mask conclusion.
- **The legend's words carry meaning Jev uses.** A name like "Pharmacy" pulls the search toward related icons, and a symbol missing from the legend shows up as errors on its nearest look-alike.

## Next steps

1. Move from one tile to several held-out tiles, and compare methods as means over at least 3 runs.
2. Use the colour mask for screening, where it clearly helps, and test it there on its own.
3. Make "ask again when unsure" the default class check.
4. Search with arbitrary codes instead of legend names, and confirm with repeat runs.
5. Fix duplicate and off-centre points: a merge radius of one icon width, and re-centring each point on the symbol.
6. Later: the faded "restricted access" icons (on hold), digital topographic maps, then scans and the energy-infrastructure maps found earlier.
