"""Renderers shared by every CLI command: Rich for humans, JSON for scripts.

Each renderer is a free function. Human output uses `rich.console.Console`
and lands on stdout; JSON output goes through `json.dumps` and lands on
stdout too. Errors and logs are emitted on stderr by the command layer.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from ..services import BaselineOutcome, BaselineRecord


_DB_RELATIVE_PATH = (".codeguard", "codeguard.db")


def _database_path(project_root: str) -> Path:
    return Path(project_root).joinpath(*_DB_RELATIVE_PATH)


def _json_default(value: object) -> str:
    if isinstance(value, datetime):
        return value.isoformat()
    return str(value)


def _print_json(payload: dict) -> None:
    print(json.dumps(payload, default=_json_default, indent=2))


def render_baseline_created(
    outcome: BaselineOutcome,
    *,
    json_output: bool,
) -> None:
    """Show the baseline summary on stdout in either Rich or JSON form."""
    record = outcome.record
    snapshot = record.snapshot
    db_path = _database_path(snapshot.project_root)

    if json_output:
        _print_json(
            {
                "ok": True,
                "baseline_id": record.baseline_id,
                "project_root": snapshot.project_root,
                "file_count": len(snapshot.files),
                "created_at": record.created_at,
                "database_path": str(db_path),
                "skipped": [list(item) for item in outcome.skipped],
            }
        )
        return

    console = Console()
    body = (
        f"[bold]Project:[/bold]   {snapshot.project_root}\n"
        f"[bold]Files:[/bold]     {len(snapshot.files)}\n"
        f"[bold]Created:[/bold]   {record.created_at.isoformat(sep=' ')}\n"
        f"[bold]Database:[/bold]  {db_path}"
    )
    console.print(
        Panel(
            body,
            title="[green]\u2713 Baseline saved[/green]",
            title_align="left",
            border_style="green",
        )
    )

    if outcome.skipped:
        table = Table(title="Skipped files", title_justify="left")
        table.add_column("Path", overflow="fold")
        table.add_column("Reason")
        for path, reason in outcome.skipped:
            table.add_row(path, reason)
        console.print(table)


def render_baseline_already_exists(
    existing: BaselineRecord,
    *,
    json_output: bool,
) -> None:
    """Show the existing-baseline message on stdout in either Rich or JSON form."""
    if json_output:
        _print_json(
            {
                "ok": False,
                "error": "baseline_already_exists",
                "existing": {
                    "baseline_id": existing.baseline_id,
                    "created_at": existing.created_at,
                },
            }
        )
        return

    console = Console()
    body = (
        f"[bold]Created:[/bold]  {existing.created_at.isoformat(sep=' ')}\n"
        "Use [bold]--force[/bold] to re-baseline."
    )
    console.print(
        Panel(
            body,
            title="[red]\u2717 Baseline already exists[/red]",
            title_align="left",
            border_style="red",
        )
    )
