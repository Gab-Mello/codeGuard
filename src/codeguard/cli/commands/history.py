"""`codeguard history` — list past scans newest-first."""

from __future__ import annotations

import logging
import sqlite3
import sys
from pathlib import Path
from typing import Annotated

import typer

from ...services import MonitoringService
from ..app import (
    EXIT_INVALID_USAGE,
    EXIT_OK,
    EXIT_RUNTIME_ERROR,
    app,
)
from ..output import render_history, render_scan_no_baseline
from ..paths import database_path, validate_project_path


_logger = logging.getLogger(__name__)


@app.command("history")
def history(
    path: Annotated[
        Path,
        typer.Argument(
            help="Project directory to inspect. Defaults to the current directory.",
        ),
    ] = Path("."),
    limit: Annotated[
        int | None,
        typer.Option(
            "--limit",
            "-n",
            help="Cap the number of rows; defaults to all scans.",
            min=1,
        ),
    ] = None,
    json_output: Annotated[
        bool,
        typer.Option(
            "--json",
            help="Emit the history as a JSON object on stdout.",
        ),
    ] = False,
) -> None:
    """List persisted scans newest-first, optionally capped with --limit."""
    resolved = validate_project_path(path)
    if not database_path(resolved).exists():
        render_scan_no_baseline(json_output=json_output)
        raise typer.Exit(EXIT_INVALID_USAGE)

    service = MonitoringService()
    try:
        records = service.list_history(resolved, limit=limit)
    except typer.Exit:
        raise
    except sqlite3.OperationalError as exc:
        _logger.exception("sqlite operational error")
        print(f"error: database error: {exc}", file=sys.stderr)
        raise typer.Exit(EXIT_RUNTIME_ERROR)
    except Exception as exc:
        _logger.exception("history failed")
        print(f"error: {exc}", file=sys.stderr)
        raise typer.Exit(EXIT_RUNTIME_ERROR)

    render_history(
        str(resolved),
        records,
        limit=limit,
        json_output=json_output,
    )
    raise typer.Exit(EXIT_OK)

