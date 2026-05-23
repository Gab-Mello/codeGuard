"""Renderer for `codeguard status`: baseline + latest scan summary."""

from __future__ import annotations

from rich.console import Console
from rich.panel import Panel

from ...services import BaselineRecord, ScanRecord
from ..paths import database_path
from ._shared import _format_relative, _print_json, _scan_record_to_json


def render_status(
    project_root: str,
    baseline: BaselineRecord,
    latest_scan: ScanRecord | None,
    *,
    json_output: bool,
) -> None:
    """Show whether a baseline exists, when, and how the latest scan went."""
    db_path = database_path(project_root)

    if json_output:
        _print_json(
            {
                "ok": True,
                "project_root": project_root,
                "database_path": str(db_path),
                "baseline": {
                    "baseline_id": baseline.baseline_id,
                    "created_at": baseline.created_at,
                    "file_count": len(baseline.snapshot.files),
                },
                "latest_scan": (
                    _scan_record_to_json(latest_scan) if latest_scan else None
                ),
                "clean": (
                    None if latest_scan is None else latest_scan.change_count == 0
                ),
            }
        )
        return

    if latest_scan is None:
        title = "[blue]\u2139 Baseline ready (no scans yet)[/blue]"
        border = "blue"
    elif latest_scan.change_count == 0:
        title = "[green]\u2713 Clean[/green]"
        border = "green"
    else:
        title = "[yellow]\u26a0 Changes detected[/yellow]"
        border = "yellow"

    baseline_line = (
        f"#{baseline.baseline_id} \u00b7 "
        f"{baseline.created_at.isoformat(sep=' ')} "
        f"({_format_relative(baseline.created_at)}) \u00b7 "
        f"{len(baseline.snapshot.files)} files"
    )
    if latest_scan is None:
        scan_line = "no scans yet"
    else:
        duration_ms = int(
            (latest_scan.finished_at - latest_scan.started_at).total_seconds() * 1000
        )
        scan_line = (
            f"#{latest_scan.scan_id} \u00b7 "
            f"{latest_scan.started_at.isoformat(sep=' ')} "
            f"({_format_relative(latest_scan.started_at)}) \u00b7 "
            f"{latest_scan.change_count} changes \u00b7 "
            f"{latest_scan.critical_count} critical \u00b7 "
            f"{duration_ms} ms"
        )

    body = (
        f"[bold]Project:[/bold]    {project_root}\n"
        f"[bold]Database:[/bold]   {db_path}\n"
        f"[bold]Baseline:[/bold]   {baseline_line}\n"
        f"[bold]Last scan:[/bold]  {scan_line}"
    )
    Console().print(
        Panel(body, title=title, title_align="left", border_style=border)
    )
