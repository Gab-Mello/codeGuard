"""Command modules. Importing each one registers it against the Typer app."""

from . import alerts, history, init, scan, status  # noqa: F401  (import side-effect: registers commands)

__all__: list[str] = []
