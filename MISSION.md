# Mission: Workflow engines for a reproducible research pipeline

## Why
The map-digitizer paper must let anyone regenerate every table and figure from a clean checkout with a few commands. Choosing (and later running) the workflow engine that drives the experiment grid (areas × zooms × scales × k × methods × ablations) is the decision that makes that possible. This is Q1 in `docs/pipeline-spec.md`.

## Success looks like
- Can explain, for Make, Snakemake, DVC and a hand-written runner, how each decides what to re-run, and predict whether a given change will re-run a stage.
- Can make and defend the Q1 decision for this project in a few sentences.
- Can read and edit the chosen engine's pipeline file for this repo (rules/stages, the parameter grid, dry runs).

## Constraints
- Learning happens alongside building the pipeline. Lessons must be short and tied directly to this repo.
- The stack is already Docker Compose based (render, db, later ml).

## Out of scope
- Cluster/cloud executors, workflow languages beyond these four (Nextflow, CWL, Airflow), CI setup.
