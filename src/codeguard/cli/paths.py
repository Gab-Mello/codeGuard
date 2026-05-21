"""CLI-side path layout: the per-project database location."""

from __future__ import annotations

from pathlib import Path


_DB_RELATIVE_PATH = (".codeguard", "codeguard.db")


def database_path(project_root: str | Path) -> Path:
    """Return `<project_root>/.codeguard/codeguard.db` for any project root."""
    return Path(project_root).joinpath(*_DB_RELATIVE_PATH)
