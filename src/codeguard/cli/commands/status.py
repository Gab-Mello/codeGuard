"""`codeguard status` — read-only summary of baseline + latest scan state."""

from __future__ import annotations

import logging
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
from ..output import render_scan_no_baseline, render_status
from ..paths import database_path


_logger = logging.getLogger(__name__)


@app.command("status")
def status(
    path: Annotated[
        Path,
        typer.Argument(
            help="Project directory to inspect. Defaults to the current directory.",
        ),
    ] = Path("."),
    json_output: Annotated[
        bool,
        typer.Option(
            "--json",
            help="Emit the status as a JSON object on stdout.",
        ),
    ] = False,
) -> None:
    """Report whether a baseline exists, when it was taken, and the latest scan."""
    if not path.exists():
        print(f"error: path not found: {path}", file=sys.stderr)
        raise typer.Exit(EXIT_INVALID_USAGE)
    if not path.is_dir():
        print(f"error: not a directory: {path}", file=sys.stderr)
        raise typer.Exit(EXIT_INVALID_USAGE)

    resolved = path.resolve()
    if not database_path(resolved).exists():
        render_scan_no_baseline(json_output=json_output)
        raise typer.Exit(EXIT_INVALID_USAGE)

    service = MonitoringService()
    try:
        baseline = service.latest_baseline(resolved)
        if baseline is None:
            render_scan_no_baseline(json_output=json_output)
            raise typer.Exit(EXIT_INVALID_USAGE)
        history = service.list_history(resolved, limit=1)
    except typer.Exit:
        raise
    except Exception as exc:
        _logger.exception("status failed")
        print(f"error: {exc}", file=sys.stderr)
        raise typer.Exit(EXIT_RUNTIME_ERROR)

    latest_scan = history[0] if history else None
    render_status(
        str(resolved),
        baseline,
        latest_scan,
        json_output=json_output,
    )
    raise typer.Exit(EXIT_OK)
