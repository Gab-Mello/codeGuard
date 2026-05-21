"""Typer application root: global options, logging setup, and exit codes."""

from __future__ import annotations

import logging
import sys
from typing import Annotated

import typer

from .. import __version__


EXIT_OK = 0
EXIT_RUNTIME_ERROR = 1
EXIT_INVALID_USAGE = 2
EXIT_CRITICAL_ALERTS = 3


app = typer.Typer(
    help="Snapshot a project's trusted state and detect unexpected changes.",
    no_args_is_help=True,
    add_completion=False,
    rich_markup_mode="rich",
)


def _configure_logging(verbose: bool) -> None:
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        stream=sys.stderr,
        force=True,
    )


def _print_version_and_exit(value: bool) -> None:
    if value:
        typer.echo(f"CodeGuard v{__version__}")
        raise typer.Exit(EXIT_OK)


@app.callback()
def _global_options(
    verbose: Annotated[
        bool,
        typer.Option(
            "--verbose",
            "-v",
            help="Enable DEBUG-level logging on stderr.",
        ),
    ] = False,
    version: Annotated[
        bool,
        typer.Option(
            "--version",
            help="Show the CodeGuard version and exit.",
            is_eager=True,
            callback=_print_version_and_exit,
        ),
    ] = False,
) -> None:
    """Configure logging once per invocation, before any subcommand runs."""
    _configure_logging(verbose)


from . import commands  # noqa: E402,F401  (import side-effect: registers commands)
