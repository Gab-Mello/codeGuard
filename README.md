# CodeGuard

A command-line tool that snapshots a project's trusted state and detects unexpected changes — with severity-aware alerts for the files that matter most (`.env`, dependency manifests, Dockerfiles, migrations, generated mocks).

## Why

In the current AI-coding era, AI assistants, scripts, and automation tools frequently modify project files. That's often useful, but it can silently change critical files. CodeGuard lets you snapshot a trusted state of a project and later see exactly what changed.

A CLI fits this job naturally: it lives next to the other developer tools you already use (`git`, `pytest`, `docker`), it's scriptable, and it plugs into CI through exit codes and JSON output.

CodeGuard is not a replacement for Git: Git tracks the changes you make on purpose, while CodeGuard watches the working tree against a trusted baseline and flags edits — committed or not — that you may not have meant to keep.

## Status

`v0.1` — all five commands implemented and CI-ready. See [`docs/architecture.md`](docs/architecture.md) for the design overview.

## Requirements

- Python 3.10+
- Dependencies in `requirements.txt` (`typer`, `rich`). SQLite is part of the Python standard library.

## Install

```bash
pip install -r requirements.txt
```

The repository is runnable without installation: `python3 main.py <command>` works from a clone.

## Usage

```text
codeguard init    [PATH] [--force] [--json]                          # snapshot the trusted baseline
codeguard review  [PATH] [--top N] [--json] [--fail-on-critical]     # daily-use: prioritised view of what changed
codeguard scan    [PATH] [--json] [--fail-on-critical]               # verbose / CI-friendly form of review
codeguard status  [PATH] [--json]                                    # show baseline + latest scan
codeguard alerts  [PATH] [--scan-id N] [--severity LEVEL] [--json]   # list alerts for a scan
codeguard history [PATH] [--limit N | -n N] [--json]                 # list previous scans
```

`review` is the command to reach for after an AI assistant or script edits your project: it runs a scan, then surfaces the items most worth a human's attention along with concrete next steps. `scan` is the same operation with the full unfiltered output, suited to CI logs.

`PATH` defaults to the current directory. The per-project database lives at `<PATH>/.codeguard/codeguard.db`.

Global options (before the subcommand): `--verbose` (raise log level to INFO), `--version`.

## Example session

```bash
$ codeguard init                      # snapshot the baseline
$ codeguard review                    # clean — no changes
$ echo "SECRET=changed" >> .env       # something modifies a tracked file
$ codeguard review --fail-on-critical # CRITICAL alert with next-step suggestions; exit 3
$ codeguard history                   # both scans, newest first
$ codeguard alerts --scan-id 2        # the alerts persisted for scan #2
```

## Exit codes

| Code | Meaning |
|------|---------|
| `0`  | Success |
| `1`  | Runtime error (DB error, unexpected exception) |
| `2`  | Invalid usage (bad path, missing baseline, scan not found, bad option) |
| `3`  | CRITICAL alerts found (only when `review --fail-on-critical` or `scan --fail-on-critical` is used) |

Every command also accepts `--json` for machine-readable output on stdout. Errors and logs go to stderr.

## Integration

CodeGuard's exit codes and `--json` output make it easy to wire into hooks and CI.

### Pre-commit hook

Drop this in `.git/hooks/pre-commit` (and `chmod +x`) to block commits when CRITICAL alerts fire:

```sh
#!/bin/sh
python /path/to/codeGuard/main.py review . --fail-on-critical
```

### GitHub Actions

```yaml
- run: pip install -r requirements.txt
- run: python main.py init . --force
- run: python main.py scan . --fail-on-critical
```

The first run captures a baseline against the freshly checked-out tree; the second run scans the same tree (after any in-job mutations like dependency installs) and fails the job on CRITICAL alerts. Use `scan` rather than `review` here: CI logs benefit from the full unfiltered table.

## Project layout

- `src/codeguard/domain/` — pure data types (no I/O).
- `src/codeguard/core/` — scanner, hasher, differ, alert rules.
- `src/codeguard/persistence/` — SQLite database and repositories.
- `src/codeguard/services/` — `MonitoringService` facade.
- `src/codeguard/cli/` — Typer commands and renderers.
- `docs/architecture.md` — class diagram, OOP map, sequence diagrams.

## License

For educational use (college Object-Oriented Programming project).
