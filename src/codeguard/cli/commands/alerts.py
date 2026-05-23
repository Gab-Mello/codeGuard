"""`codeguard alerts` — browse persisted alerts from past scans."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Annotated

import typer

from ...services import MonitoringService, ScanNotFoundError, Severity
from ..app import EXIT_INVALID_USAGE, EXIT_OK, app
from ..output import render_alerts_view, render_scan_not_found
from ..paths import handle_runtime_error, require_initialized, validate_project_path


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
    require_initialized(resolved, json_output=json_output)

    service = MonitoringService()
    try:
        record, scan_alerts = service.list_alerts(resolved, scan_id=scan_id)
    except ScanNotFoundError as exc:
        render_scan_not_found(exc.scan_id, json_output=json_output)
        raise typer.Exit(EXIT_INVALID_USAGE)
    except typer.Exit:
        raise
    except Exception as exc:
        raise handle_runtime_error(exc, logger=_logger, context="alerts")

    render_alerts_view(
        record,
        scan_alerts,
        severity_filter=severity,
        json_output=json_output,
    )
    raise typer.Exit(EXIT_OK)

