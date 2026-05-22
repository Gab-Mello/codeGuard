"""`codeguard scan` — diff the project against its baseline and report changes."""

from __future__ import annotations

import logging
import sqlite3
import sys
from pathlib import Path
from typing import Annotated

import typer

from ...services import BaselineNotFoundError, MonitoringService
from ..app import (
    EXIT_CRITICAL_ALERTS,
    EXIT_INVALID_USAGE,
    EXIT_OK,
    EXIT_RUNTIME_ERROR,
    app,
)
from ..output import render_scan_no_baseline, render_scan_result
from ..paths import database_path, validate_project_path


_logger = logging.getLogger(__name__)


@app.command("scan")
def scan(
    path: Annotated[
        Path,
        typer.Argument(
            help="Project directory to scan. Defaults to the current directory.",
        ),
    ] = Path("."),
    json_output: Annotated[
        bool,
        typer.Option(
            "--json",
            help="Emit the scan result as a JSON object on stdout.",
        ),
    ] = False,
    fail_on_critical: Annotated[
        bool,
        typer.Option(
            "--fail-on-critical",
            help="Exit with code 3 when CRITICAL alerts fire.",
        ),
    ] = False,
) -> None:
    """Diff the project against its baseline; persist and display changes and alerts."""
    resolved = validate_project_path(path)
    if not database_path(resolved).exists():
        render_scan_no_baseline(json_output=json_output)
        raise typer.Exit(EXIT_INVALID_USAGE)

    service = MonitoringService()
    try:
        outcome = service.scan(resolved)
    except BaselineNotFoundError:
        render_scan_no_baseline(json_output=json_output)
        raise typer.Exit(EXIT_INVALID_USAGE)
    except sqlite3.OperationalError as exc:
        _logger.exception("sqlite operational error")
        print(f"error: database error: {exc}", file=sys.stderr)
        raise typer.Exit(EXIT_RUNTIME_ERROR)
    except Exception as exc:
        _logger.exception("scan failed")
        print(f"error: {exc}", file=sys.stderr)
        raise typer.Exit(EXIT_RUNTIME_ERROR)

    render_scan_result(outcome, json_output=json_output)
    if fail_on_critical and outcome.record.critical_count > 0:
        raise typer.Exit(EXIT_CRITICAL_ALERTS)
    raise typer.Exit(EXIT_OK)

