# Workflow Engines Resources

## Knowledge

- [Snakemake docs: Snakefiles and Rules](https://snakemake.readthedocs.io/en/stable/snakefiles/rules.html)
  Official reference for rules, wildcards and `expand()`. Use for: how one rule covers a whole grid of files.
- [Snakemake docs: Command line interface](https://snakemake.readthedocs.io/en/stable/executing/cli.html)
  All flags, including `--rerun-triggers` (default: code input mtime params software-env, confirmed in `snakemake --help`, v9.27.2), `-n` dry run, `--dag`, `--summary`. Use for: what will re-run and why.
- [Snakemake docs: Distribution and reproducibility](https://snakemake.readthedocs.io/en/stable/snakefiles/deployment.html)
  The `container:` directive takes `docker://` image URLs, but jobs run through **Apptainer** (`--sdm apptainer`), not the Docker engine. Use for: container decisions.
- [DVC docs: Defining pipelines](https://doc.dvc.org/user-guide/pipelines/defining-pipelines)
  Short, readable intro to stages (`cmd`, `deps`, `params`, `outs`) and content-hash change detection. Use for: the DVC mental model.
- [DVC docs: dvc.yaml files](https://doc.dvc.org/user-guide/project-structure/dvcyaml-files)
  Reference for `foreach` and `matrix` (one stage per combination) and `dvc.lock` hashes. Use for: grids in DVC.
- [DVC docs: dvc repro](https://doc.dvc.org/command-reference/repro)
  Re-running pipelines, `--dry`, output caching, `dvc push` to remote storage.
- [GNU Make manual: How Make Works](https://www.gnu.org/software/make/manual/html_node/How-Make-Works.html)
  The timestamp rule. Not read during setup (the site returned HTTP 429); the behaviour was instead verified by experiment with GNU Make 4.4.1.

## Wisdom (Communities)

- [Stack Overflow: snakemake tag](https://stackoverflow.com/questions/tagged/snakemake)
  Active Q&A, often answered by maintainers. Use for: "how do I express this grid/dependency" questions.
- [Stack Overflow: dvc tag](https://stackoverflow.com/questions/tagged/dvc)
  Use for: DVC pipeline and remote-storage questions.

## Gaps
- No neutral, primary-source comparison of Snakemake vs DVC for ML/geo research pipelines. The lesson builds that comparison from each tool's own docs.
