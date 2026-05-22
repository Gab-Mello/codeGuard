"""`codeguard init` — capture the trusted baseline of a project."""

from __future__ import annotations

import logging
import sqlite3
import sys
from pathlib import Path
from typing import Annotated

import typer

from ...services import BaselineAlreadyExistsError, MonitoringService
from ..app import (
    EXIT_INVALID_USAGE,
    EXIT_OK,
    EXIT_RUNTIME_ERROR,
    app,
)
from ..output import render_baseline_already_exists, render_baseline_created
from ..paths import validate_project_path


_logger = logging.getLogger(__name__)


@app.command("init")
def init(
    path: Annotated[
        Path,
        typer.Argument(
            help="Project directory to baseline. Defaults to the current directory.",
        ),
    ] = Path("."),
    force: Annotated[
        bool,
        typer.Option(
            "--force",
            help="Replace any existing baseline for this project.",
        ),
    ] = False,
    json_output: Annotated[
        bool,
        typer.Option(
            "--json",
            help="Emit the result as a JSON object on stdout.",
        ),
    ] = False,
) -> None:
    """Snapshot the project's files and store them as the trusted baseline."""
    resolved = validate_project_path(path)

    service = MonitoringService()
    try:
        outcome = service.create_baseline(resolved, force=force)
    except BaselineAlreadyExistsError as exc:
        render_baseline_already_exists(exc.existing, json_output=json_output)
        raise typer.Exit(EXIT_INVALID_USAGE)
    except sqlite3.OperationalError as exc:
        _logger.exception("sqlite operational error")
        print(f"error: database error: {exc}", file=sys.stderr)
        raise typer.Exit(EXIT_RUNTIME_ERROR)
    except Exception as exc:
        _logger.exception("init failed")
        print(f"error: {exc}", file=sys.stderr)
        raise typer.Exit(EXIT_RUNTIME_ERROR)

    render_baseline_created(outcome, json_output=json_output)
    raise typer.Exit(EXIT_OK)

