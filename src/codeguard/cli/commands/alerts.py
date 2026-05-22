"""`codeguard alerts` — browse persisted alerts from past scans."""

from __future__ import annotations

import logging
import sqlite3
import sys
from pathlib import Path
from typing import Annotated

import typer

from ...services import MonitoringService, ScanNotFoundError, Severity
from ..app import (
    EXIT_INVALID_USAGE,
    EXIT_OK,
    EXIT_RUNTIME_ERROR,
    app,
)
from ..output import (
    render_alerts_view,
    render_scan_no_baseline,
    render_scan_not_found,
)
from ..paths import database_path, validate_project_path


_logger = logging.getLogger(__name__)


@app.command("alerts")
def alerts(
    path: Annotated[
        Path,
        typer.Argument(
            help="Project directory to inspect. Defaults to the current directory.",
        ),
    ] = Path("."),
    scan_id: Annotated[
        int | None,
        typer.Option(
            "--scan-id",
            help="Show alerts for a specific scan id. Defaults to the latest scan.",
        ),
    ] = None,
    severity: Annotated[
        Severity | None,
        typer.Option(
            "--severity",
            help="Filter rows to a single severity (LOW|MEDIUM|HIGH|CRITICAL).",
            case_sensitive=False,
        ),
    ] = None,
    json_output: Annotated[
        bool,
        typer.Option(
            "--json",
            help="Emit the alerts view as a JSON object on stdout.",
        ),
    ] = False,
) -> None:
    """Show alerts persisted for a scan, optionally filtered by severity."""
    resolved = validate_project_path(path)
    if not database_path(resolved).exists():
        render_scan_no_baseline(json_output=json_output)
        raise typer.Exit(EXIT_INVALID_USAGE)

    service = MonitoringService()
    try:
        record, scan_alerts = service.list_alerts(resolved, scan_id=scan_id)
    except ScanNotFoundError as exc:
        render_scan_not_found(exc.scan_id, json_output=json_output)
        raise typer.Exit(EXIT_INVALID_USAGE)
    except typer.Exit:
        raise
    except sqlite3.OperationalError as exc:
        _logger.exception("sqlite operational error")
        print(f"error: database error: {exc}", file=sys.stderr)
        raise typer.Exit(EXIT_RUNTIME_ERROR)
    except Exception as exc:
        _logger.exception("alerts failed")
        print(f"error: {exc}", file=sys.stderr)
        raise typer.Exit(EXIT_RUNTIME_ERROR)

    render_alerts_view(
        record,
        scan_alerts,
        severity_filter=severity,
        json_output=json_output,
    )
    raise typer.Exit(EXIT_OK)

