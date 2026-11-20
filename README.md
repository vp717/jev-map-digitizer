# map-digitizer

Legend-driven point-symbol detection on maps with TypeSafe Jev, compared against trained detectors.
Design: [docs/design.md](docs/design.md). Pipeline spec: [docs/pipeline-spec.md](docs/pipeline-spec.md).
Literature review: [docs/research/](docs/research/).

## Reproduce

Requirements: Docker (Compose v2), [uv](https://docs.astral.sh/uv/), and for GPU stages the [NVIDIA Container Toolkit](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/latest/install-guide.html) (an NVIDIA driver supporting CUDA 12.6). API keys go in a git-ignored `.env`: `TYPESAFE_API_KEY=...`, `ANTHROPIC_API_KEY=...`.

```sh
uv sync                                   # installs Snakemake (pinned) on the host
docker compose build render ml
docker compose up -d --wait db
uv run snakemake -n                       # dry run: what would run and why
uv run snakemake --cores 2                # run everything that is stale
```

The experiment is defined entirely by `config/experiments/osm_phase1.yaml`; use `--configfile` for another.
Outputs land in `out/<experiment>/`, each with a `manifest.json` (git commit, dirty flag, image id, input md5s, params).

The OSM extract is pinned by md5. Geofabrik's `-latest` file changes daily, so on a fresh machine
`fetch` will fail the check unless you restore the archived extract into `data/`.

## Run a single stage by hand

```sh
docker compose run --rm --user "$(id -u):$(id -g)" render mapdig --help
docker compose run --rm --user "$(id -u):$(id -g)" render mapdig overlay \
  out/osm_phase1/maps/freiburg_centre/z17_s1/map.tif out/osm_phase1/maps/freiburg_centre/z17_s1/gt.gpkg \
  out/check.png --window 1700 1400 600 420
uv run snakemake out/osm_phase1/class_counts_z17.csv --cores 1   # icon counts used to choose classes
```

Renders are only deterministic with PostgreSQL parallel query off; `docker-compose.yml` sets this.
