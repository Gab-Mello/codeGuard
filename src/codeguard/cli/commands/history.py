"""`codeguard history` — list past scans newest-first."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Annotated

import typer

from ...services import MonitoringService
from ..app import EXIT_INVALID_USAGE, EXIT_OK, app
from ..output import render_history
from ..paths import handle_runtime_error, require_initialized, validate_project_path


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
    require_initialized(resolved, json_output=json_output)

    service = MonitoringService()
    try:
        records = service.list_history(resolved, limit=limit)
    except typer.Exit:
        raise
    except Exception as exc:
        raise handle_runtime_error(exc, logger=_logger, context="history")

    render_history(
        str(resolved),
        records,
        limit=limit,
        json_output=json_output,
    )
    raise typer.Exit(EXIT_OK)

