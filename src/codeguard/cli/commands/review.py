"""`codeguard review` — prioritised, action-oriented view of the latest scan."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Annotated

import typer

from ...services import BaselineNotFoundError, MonitoringService
from ..app import (
    EXIT_CRITICAL_ALERTS,
    EXIT_INVALID_USAGE,
    EXIT_OK,
    app,
)
from ..output import render_review_summary, render_scan_no_baseline
from ..paths import handle_runtime_error, require_initialized, validate_project_path


_logger = logging.getLogger(__name__)


@app.command("review")
def review(
    path: Annotated[
        Path,
        typer.Argument(
            help="Project directory to review. Defaults to the current directory.",
        ),
    ] = Path("."),
    top: Annotated[
        int,
        typer.Option(
            "--top",
            min=1,
            help="Maximum number of items to surface in the review list.",
        ),
    ] = 5,
    json_output: Annotated[
        bool,
        typer.Option(
            "--json",
            help="Emit the review as a JSON object on stdout.",
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
    """Run a scan and surface the items most worth a human's attention right now."""
    resolved = validate_project_path(path)
    require_initialized(resolved, json_output=json_output)

    service = MonitoringService()
    try:
        outcome = service.scan(resolved)
    except BaselineNotFoundError:
        render_scan_no_baseline(json_output=json_output)
        raise typer.Exit(EXIT_INVALID_USAGE)
    except Exception as exc:
        raise handle_runtime_error(exc, logger=_logger, context="review")

    render_review_summary(outcome, top=top, json_output=json_output)
    if fail_on_critical and outcome.record.critical_count > 0:
        raise typer.Exit(EXIT_CRITICAL_ALERTS)
    raise typer.Exit(EXIT_OK)
