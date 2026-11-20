"""Legend label handling: optionally replace legend names with arbitrary codes (change 6).

Codes come from a seeded permutation over the legend rows, so 'symbol 37' carries no order
or meaning. The scoring class (gt_label) is never changed, only what Jev is shown.
"""
import numpy as np

def anonymize(entries, seed=17):
    """Return entries with 'label' replaced by 'symbol NN' (and the original kept as 'name')."""
    perm = np.random.default_rng(seed).permutation(len(entries))
    out = []
    for e, p in zip(sorted(entries, key=lambda x: x["index"]), perm):
        out.append({**e, "name": e["label"], "label": f"symbol {10 + int(p)}"})
    return out
