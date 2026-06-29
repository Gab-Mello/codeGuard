# CodeGuard

A command-line tool that snapshots a project's trusted state and detects unexpected changes, with severity-aware alerts for the files that matter most (`.env`, dependency manifests, Dockerfiles, migrations, generated mocks).

This project was developed for an Object-Oriented Programming class.

## Why

AI assistants, scripts, and automation tools frequently modify project files. That's often useful, but it can silently change things you didn't intend to change. CodeGuard lets you snapshot a trusted state of a project and later see exactly what drifted.

CodeGuard is not a replacement for Git. Git tracks the changes you make on purpose; CodeGuard watches the working tree against a trusted baseline and flags edits (committed or not) that you may not have meant to keep.

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
python3 main.py init    [PATH] [--force] [--json]                          # snapshot the trusted baseline
python3 main.py scan    [PATH] [--json] [--fail-on-critical]               # diff against baseline; show changes and alerts
python3 main.py status  [PATH] [--json]                                    # show baseline + latest scan
python3 main.py alerts  [PATH] [--scan-id N] [--severity LEVEL] [--json]   # list alerts for a scan
python3 main.py history [PATH] [--limit N | -n N] [--json]                 # list previous scans
```

`scan` is the daily-use command after an AI assistant or script edits your project: it runs a fresh scan, persists the result, and reports the changes and alerts. Pair it with `--fail-on-critical` in CI to gate on CRITICAL alerts.

`PATH` defaults to the current directory. The per-project database lives at `<PATH>/.codeguard/codeguard.db`.

## Example session

```bash
$ python3 main.py init                      # snapshot the baseline
$ python3 main.py scan                      # clean, no changes
$ echo "SECRET=changed" >> .env             # something modifies a tracked file
$ python3 main.py scan --fail-on-critical   # CRITICAL alert; exit 3
$ python3 main.py history                   # both scans, newest first
$ python3 main.py alerts --scan-id 2        # the alerts persisted for scan #2
```

## Exit codes

| Code | Meaning |
|------|---------|
| `0`  | Success |
| `1`  | Runtime error (DB error, unexpected exception) |
| `2`  | Invalid usage (bad path, missing baseline, scan not found, bad option) |
| `3`  | CRITICAL alerts found (only with `--fail-on-critical`) |

Every command also accepts `--json` for machine-readable output on stdout; errors and logs go to stderr.

## Integration

CodeGuard's exit codes and `--json` output make it easy to wire into hooks and CI. For example, drop this in `.git/hooks/pre-commit` to block commits when CRITICAL alerts fire:

```sh
#!/bin/sh
python3 /path/to/codeGuard/main.py scan . --fail-on-critical
```

## Project layout

```
src/codeguard/
├── domain/              # Pure data + domain logic (entities, differ, rules). No I/O.
├── application/         # MonitoringService + DTOs + repository/scanner Protocols.
├── infrastructure/      # I/O adapters: filesystem (scanner) and SQLite persistence.
└── cli/                 # Typer commands, output renderers, wiring.py composition root.
```

## Architecture at a glance

CodeGuard follows a layered / Clean Architecture style. Dependencies flow inward only:

```
cli  →  application  →  domain
cli  →  infrastructure  →  domain
```

The application layer depends on Protocols, not on concrete infrastructure; the CLI's `wiring.py` injects the concrete adapters at construction time. See [`docs/architecture.md`](docs/architecture.md) for the architecture overview, OOP-concept map, command flows, and persistence model.
