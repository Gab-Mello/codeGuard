"""CLI-side path layout: the per-project database location."""

from __future__ import annotations

import sys
from pathlib import Path

import typer

from .app import EXIT_INVALID_USAGE


# Mirrored in services/monitoring_service.py — keep both in sync.
_DB_RELATIVE_PATH = (".codeguard", "codeguard.db")


def database_path(project_root: str | Path) -> Path:
    """Return `<project_root>/.codeguard/codeguard.db` for any project root."""
    return Path(project_root).joinpath(*_DB_RELATIVE_PATH)


def validate_project_path(path: Path) -> Path:
    """Validate a CLI project-root argument and return its resolved absolute form.

    Prints a one-line error to stderr and exits with `EXIT_INVALID_USAGE`
    when the path does not exist or is not a directory.
    """
    if not path.exists():
        print(f"error: path not found: {path}", file=sys.stderr)
        raise typer.Exit(EXIT_INVALID_USAGE)
    if not path.is_dir():
        print(f"error: not a directory: {path}", file=sys.stderr)
        raise typer.Exit(EXIT_INVALID_USAGE)
    return path.resolve()
