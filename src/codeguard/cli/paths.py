"""CLI-side path layout: the per-project database location."""

from __future__ import annotations

import logging
import sqlite3
import sys
from pathlib import Path

import typer

from ..services import DB_RELATIVE_PATH
from .app import EXIT_INVALID_USAGE, EXIT_RUNTIME_ERROR


def database_path(project_root: str | Path) -> Path:
    """Return `<project_root>/.codeguard/codeguard.db` for any project root."""
    return Path(project_root).joinpath(*DB_RELATIVE_PATH)


def require_initialized(project_root: Path, *, json_output: bool) -> None:
    """Render the no-baseline panel and exit 2 if the project has no database.

    Avoids scaffolding `.codeguard/` as a side effect on uninitialised paths
    by checking for the database file before any service call.
    """
    if database_path(project_root).exists():
        return
    from .output import render_scan_no_baseline

    render_scan_no_baseline(json_output=json_output)
    raise typer.Exit(EXIT_INVALID_USAGE)


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


def handle_runtime_error(
    exc: Exception, *, logger: logging.Logger, context: str
) -> typer.Exit:
    """Log + render a one-line stderr error and return a `typer.Exit(1)`.

    Distinguishes `sqlite3.OperationalError` (prefixed `database error:`)
    from any other unexpected exception. Callers `raise` the returned
    `typer.Exit` so the CLI exits with `EXIT_RUNTIME_ERROR`.
    """
    if isinstance(exc, sqlite3.OperationalError):
        logger.exception("sqlite operational error")
        print(f"error: database error: {exc}", file=sys.stderr)
    else:
        logger.exception("%s failed", context)
        print(f"error: {exc}", file=sys.stderr)
    return typer.Exit(EXIT_RUNTIME_ERROR)
