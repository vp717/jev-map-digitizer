"""Content-addressed cache for hosted-model calls (Jev, Opus).

Key = sha256 of the canonical request description, with every image replaced by the sha256
of its bytes. Modes: online (use cache, call on miss), offline (miss is an error; paper
replays), refresh (always call, overwrite). Each entry stores the request description,
the response, token usage, latency and time, so cost can be summed later.
"""
import datetime, hashlib, json, os, time

def sha256_bytes(b):
    return hashlib.sha256(b).hexdigest()

class CacheMiss(RuntimeError):
    pass

class ApiCache:
    def __init__(self, root="cache/api", mode="online"):
        if mode not in ("online", "offline", "refresh"):
            raise ValueError(mode)
        self.root, self.mode = root, mode
        self.hits = self.calls = 0

    def _path(self, provider, key):
        return os.path.join(self.root, provider, key[:2], key + ".json")

    def get_or_call(self, provider, request, call):
        """request: JSON-able description (images as sha256). call(): -> (response_json, usage_dict)."""
        key = hashlib.sha256(json.dumps(request, sort_keys=True).encode()).hexdigest()
        path = self._path(provider, key)
        if self.mode != "refresh" and os.path.exists(path):
            self.hits += 1
            with open(path) as fh:
                return json.load(fh)
        if self.mode == "offline":
            raise CacheMiss(f"{provider} request {key} not in cache (offline mode)")
        t0 = time.time()
        response, usage = call()
        entry = {"key": key, "provider": provider, "request": request, "response": response, "usage": usage,
                 "latency_s": round(time.time() - t0, 3),
                 "called_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")}
        os.makedirs(os.path.dirname(path), exist_ok=True)
        tmp = path + ".tmp"
        with open(tmp, "w") as fh:
            json.dump(entry, fh)
        os.replace(tmp, path)
        self.calls += 1
        return entry
