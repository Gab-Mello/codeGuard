"""Renderer for `codeguard history`: persisted scans newest-first."""

from __future__ import annotations

from rich.console import Console
from rich.table import Table

from ...services import ScanRecord
from ._shared import _print_json, _scan_record_to_json


def render_history(
    project_root: str,
    records: list[ScanRecord],
    *,
    limit: int | None,
    json_output: bool,
) -> None:
    """Show persisted scans newest-first as a table or JSON object."""
    if json_output:
        _print_json(
            {
                "ok": True,
                "project_root": project_root,
                "scan_count": len(records),
                "limit": limit,
                "scans": [_scan_record_to_json(r) for r in records],
            }
        )
        return

    console = Console()
    header = f"[bold]Scan history[/bold] \u00b7 {len(records)} scans"
    if limit is not None:
        header += f" \u00b7 limit {limit}"
    console.print(header)
    if not records:
        console.print("[dim](no scans yet)[/dim]")
        return

    table = Table(title_justify="left")
    table.add_column("ID", justify="right", no_wrap=True)
    table.add_column("Started", no_wrap=True)
    table.add_column("Changes", justify="right", no_wrap=True)
    table.add_column("Alerts", justify="right", no_wrap=True)
    table.add_column("Critical", justify="right", no_wrap=True)
    table.add_column("Time", justify="right", no_wrap=True)
    for record in records:
        duration_ms = int(
            (record.finished_at - record.started_at).total_seconds() * 1000
        )
        critical_cell = (
            f"[bold red]{record.critical_count}[/bold red]"
            if record.critical_count > 0
            else f"[dim]{record.critical_count}[/dim]"
        )
        table.add_row(
            str(record.scan_id),
            record.started_at.isoformat(sep=" "),
            str(record.change_count),
            str(record.alert_count),
            critical_cell,
            f"{duration_ms} ms",
        )
    console.print(table)
