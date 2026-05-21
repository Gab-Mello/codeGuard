"""Command modules. Importing each one registers it against the Typer app."""

from . import init  # noqa: F401  (import side-effect: registers the command)

__all__: list[str] = []
