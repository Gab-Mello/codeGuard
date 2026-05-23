"""Renderers for `codeguard init`: baseline created or already exists."""

from __future__ import annotations

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from ...services import BaselineOutcome, BaselineRecord
from ..paths import database_path
from ._shared import _print_json


def render_baseline_created(
    outcome: BaselineOutcome,
    *,
    json_output: bool,
) -> None:
    """Show the baseline summary on stdout in either Rich or JSON form."""
    record = outcome.record
    snapshot = record.snapshot
    db_path = database_path(snapshot.project_root)

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
    console.print(
        "[dim]Next: run [bold]codeguard scan[/bold] to detect changes.[/dim]"
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
