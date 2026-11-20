"""TypeSafe Jev client for legend-symbol questions on map tiles, routed through the API cache."""
from mapdig.apicache import sha256_bytes

MODEL = "jev-1.14.0"
PRICE_IN = 0.042e-6   # $/input token (docs.typesafe.ai/models, checked 2026-11-19); output tokens free
IMAGE_HEADER = {"TypeSafe-Danger-Zone-Images": "true"}   # images and Box are opt-in ("Dreamer-ready")

def _symbol_phrase(label, legend_ref, use_label):
    return (f"the map symbol shown in this legend excerpt {legend_ref}, which the legend labels '{label}'"
            if use_label else f"the map symbol shown in this legend excerpt {legend_ref}")

PROMPTS = {   # versioned: changing the wording changes the cache key and must bump the version
    "v1": {
        "present": "Does `map` contain at least one instance of {symbol}? Only count symbols drawn exactly "
                   "like it (same shape and colour); ignore patches of plain background.",
        "where": "One instance in `map` of {symbol}.",
    },
}

class Jev:
    def __init__(self, cache, model=MODEL, prompt_version="v1", repeat=0):
        self.repeat = repeat   # run-level repeat number: cache key only, the request sent is unchanged
        from typesafe_sdk import TypeSafeClient
        self.client = TypeSafeClient(model=model, headers=IMAGE_HEADER)
        self.cache, self.model, self.pv = cache, model, prompt_version

    def present(self, tile_png: bytes, legend_png: bytes, label: str, use_label=True):
        """One Noul question only (stage-1 presence screening). Returns the cache entry."""
        from typesafe_sdk import Image, Noul
        p = PROMPTS[self.pv]
        request = {"model": self.model, "prompt_version": self.pv, "questions": ["present"],
                   "tile_sha256": sha256_bytes(tile_png), "legend_sha256": sha256_bytes(legend_png),
                   "label": label if use_label else None}
        if self.repeat:
            request["repeat"] = self.repeat

        def call():
            tile, legend = Image(tile_png), Image(legend_png)
            symbol = _symbol_phrase(label, str(legend), use_label)
            with self.client.attach_assets(legend):
                r = self.client.system_one(state={"map": tile},
                                           questions={"present": Noul(instructions=p["present"].format(symbol=symbol))},
                                           model=self.model)
            return r.model_dump(mode="json"), r.usage.model_dump(mode="json")

        return self.cache.get_or_call("typesafe", request, call)

    def present_batch(self, tile_png: bytes, legends, use_label=True):
        """One call, one map image, many legend excerpts: a Noul per (label, legend_png). Returns the cache entry.
        Answers are keyed q00, q01, ... in the order given."""
        from typesafe_sdk import Image, Noul
        p = PROMPTS[self.pv]
        request = {"model": self.model, "prompt_version": self.pv, "questions": "present_batch",
                   "tile_sha256": sha256_bytes(tile_png),
                   "legends": [[lab if use_label else None, sha256_bytes(b)] for lab, b in legends]}

        def call():
            tile = Image(tile_png)
            imgs = [Image(b) for _, b in legends]
            qs = {f"q{i:02d}": Noul(instructions=p["present"].format(symbol=_symbol_phrase(lab, str(img), use_label)))
                  for i, ((lab, _), img) in enumerate(zip(legends, imgs))}
            with self.client.attach_assets(imgs):
                r = self.client.system_one(state={"map": tile}, questions=qs, model=self.model)
            return r.model_dump(mode="json"), r.usage.model_dump(mode="json")

        return self.cache.get_or_call("typesafe", request, call)

    def which_symbol(self, crop_png: bytes, options, none_label="none of these", repeat=0):
        """Choice: which legend excerpt is drawn at the centre of `crop`? options: [(label, legend_png)].
        Adds a text option for 'none of these'. Returns the cache entry."""
        from typesafe_sdk import Choice, Image
        request = {"model": self.model, "prompt_version": self.pv, "questions": "which_symbol",
                   "crop_sha256": sha256_bytes(crop_png), "options": [[lab, sha256_bytes(b)] for lab, b in options],
                   "none": none_label}
        if self.repeat:   # cache-key only: the request sent to Jev is identical for every repeat
            request["repeat"] = f"run{self.repeat}-{repeat}"
        elif repeat:
            request["repeat"] = repeat

        def call():
            crop = Image(crop_png)
            criteria = {lab: Image(b) for lab, b in options}
            criteria[none_label] = "The centre of `crop` shows none of these symbols (background, text, or another symbol)."
            r = self.client.system_one(
                state={"crop": crop},
                questions={"which": Choice(instructions="Which of these legend symbols is drawn at the centre of `crop`?",
                                           criteria=criteria)},
                model=self.model)
            return r.model_dump(mode="json"), r.usage.model_dump(mode="json")

        return self.cache.get_or_call("typesafe", request, call)

    def present_and_where(self, tile_png: bytes, legend_png: bytes, label: str, use_label=True):
        """One call with two questions: Noul 'present?' and Box 'where?'. Returns the cache entry."""
        from typesafe_sdk import Box, Image, Noul
        p = PROMPTS[self.pv]
        request = {"model": self.model, "prompt_version": self.pv, "questions": ["present", "where"],
                   "tile_sha256": sha256_bytes(tile_png), "legend_sha256": sha256_bytes(legend_png),
                   "label": label if use_label else None}
        if self.repeat:
            request["repeat"] = self.repeat

        def call():
            tile, legend = Image(tile_png), Image(legend_png)
            symbol = _symbol_phrase(label, str(legend), use_label)
            with self.client.attach_assets(legend):
                r = self.client.system_one(
                    state={"map": tile},
                    questions={"present": Noul(instructions=p["present"].format(symbol=symbol)),
                               "where": Box(instructions=p["where"].format(symbol=symbol))},
                    model=self.model)
            return r.model_dump(mode="json"), r.usage.model_dump(mode="json")

        return self.cache.get_or_call("typesafe", request, call)
