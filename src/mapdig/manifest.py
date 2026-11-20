"""Provenance manifests written next to every stage output."""
import datetime, hashlib, json, os, platform, subprocess, sys, time

from mapdig import __version__

def _git(*args):
    try:
        return subprocess.run(["git", *args], capture_output=True, text=True, check=True).stdout.strip()
    except Exception:
        return None

def git_info():
    """Commit and dirty flag. Snakemake passes them in (the container may lack repo ownership)."""
    commit = os.environ.get("MAPDIG_GIT_COMMIT") or _git("rev-parse", "HEAD")
    dirty = os.environ.get("MAPDIG_GIT_DIRTY")
    dirty = bool(int(dirty)) if dirty is not None else bool(_git("status", "--porcelain"))
    return {"commit": commit, "dirty": dirty}

def file_md5(path, chunk=1 << 22):
    h = hashlib.md5()
    with open(path, "rb") as fh:
        while b := fh.read(chunk):
            h.update(b)
    return h.hexdigest()

def params_hash(params):
    return hashlib.sha256(json.dumps(params, sort_keys=True, default=str).encode()).hexdigest()[:12]

class Manifest:
    """Usage: m = Manifest("groundtruth", params, inputs=[...]); ...; m.write(path, outputs=[...])"""
    def __init__(self, stage, params, inputs=()):
        self.stage, self.params, self.inputs = stage, params, list(inputs)
        self.t0 = time.time()
        self.started = datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")
        self.extra = {}

    def write(self, path, outputs=()):
        doc = {
            "stage": self.stage,
            "params": self.params,
            "params_hash": params_hash(self.params),
            "inputs": {p: file_md5(p) for p in self.inputs if os.path.isfile(p)},
            "outputs": list(outputs),
            "git": git_info(),
            "image": os.environ.get("MAPDIG_IMAGE"),
            "mapdig_version": __version__,
            "python": sys.version.split()[0],
            "host": platform.node(),
            "started_utc": self.started,
            "seconds": round(time.time() - self.t0, 1),
            **self.extra,
        }
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        with open(path, "w") as fh:
            json.dump(doc, fh, indent=1)
