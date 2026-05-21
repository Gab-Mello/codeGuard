# CodeGuard

A command-line tool that monitors important files inside a software project so developers can detect (and review) unexpected changes.

## Why

In the current AI coding era, AI assistants, scripts, and automation tools frequently modify project files. That is often useful, but it can also silently change critical files (`.env`, dependency manifests, Dockerfiles, migrations, generated mocks…). CodeGuard lets you snapshot a trusted state of a project and later see exactly what changed, with severity-aware contextual alerts for the files that matter most.

A CLI fits this job naturally: it lives next to the other developer tools you already use (`git`, `pytest`, `docker`, `kubectl`), it's scriptable, and it plugs into CI with exit codes and JSON output.

## Status

Early development. The domain, scanning, diffing, and alert-rule layers are implemented; the persistence layer and CLI surface are next.

## Requirements

- Python 3.10+
- Dependencies in `requirements.txt` (`typer`, `rich`). SQLite is part of the Python standard library.

## Install

```bash
pip install -r requirements.txt
```

## Usage

```bash
codeguard init    [PATH]                # snapshot a project as the trusted baseline
codeguard scan    [PATH]                # scan against the baseline, raise alerts
codeguard status  [PATH]                # show whether a baseline exists and when it was taken
codeguard alerts  [PATH]                # list alerts from the latest (or a specific) scan
codeguard history [PATH]                # list previous scans
```

`PATH` defaults to the current directory. Common options:

- `--db-path PATH` — override the per-project SQLite database (default: `<project>/.codeguard/codeguard.db`).
- `--json` — emit machine-readable output for scripting and CI.
- `--fail-on-critical` — make `scan` exit with code `3` when CRITICAL alerts fire.
- `--verbose` — raise log level to DEBUG.

Exit codes: `0` success · `1` runtime error · `2` invalid usage · `3` critical alerts found (only with `--fail-on-critical`).

Until the CLI entry point is wired up, `python main.py` only verifies the project layout.

## License

For educational use (college Object-Oriented Programming project).
