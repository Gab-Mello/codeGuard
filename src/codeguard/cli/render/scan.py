"""Renderers for `codeguard scan`: scan result and the no-baseline error."""

from __future__ import annotations

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from ...services import ScanOutcome
from ._shared import (
    _CHANGE_TYPE_STYLE,
    _alert_to_json,
    _alerts_table,
    _change_size_cell,
    _change_to_json,
    _print_json,
    _sorted_changes,
)


def render_scan_result(outcome: ScanOutcome, *, json_output: bool) -> None:
    """Show the scan summary, changes, and alerts on stdout."""
    record = outcome.record
    duration_ms = int(
        (record.finished_at - record.started_at).total_seconds() * 1000
    )

    if json_output:
        _print_json(
            {
                "ok": True,
                "scan_id": record.scan_id,
                "baseline_id": record.baseline_id,
                "started_at": record.started_at,
                "finished_at": record.finished_at,
                "duration_ms": duration_ms,
                "change_count": record.change_count,
                "alert_count": record.alert_count,
                "critical_count": record.critical_count,
                "changes": [_change_to_json(c) for c in outcome.changes],
                "alerts": [_alert_to_json(a) for a in outcome.alerts],
                "skipped": [list(item) for item in outcome.skipped],
            }
        )
        return

    console = Console()
    critical_segment = (
        f"[bold red]{record.critical_count} critical[/bold red]"
        if record.critical_count > 0
        else f"[dim]{record.critical_count} critical[/dim]"
    )
    console.print(
        f"[bold]Scan #{record.scan_id}[/bold] \u00b7 "
        f"{record.change_count} changes \u00b7 "
        f"{record.alert_count} alerts \u00b7 "
        f"{critical_segment} \u00b7 "
        f"{duration_ms} ms"
    )

    if outcome.changes:
        table = Table(title="Changes", title_justify="left")
        table.add_column("Type", no_wrap=True)
        table.add_column("Path", overflow="fold")
        table.add_column("Size", justify="right", no_wrap=True)
        for change in _sorted_changes(outcome.changes):
            style = _CHANGE_TYPE_STYLE[change.change_type]
            table.add_row(
                f"[{style}]{change.change_type.value}[/{style}]",
                change.relative_path,
                _change_size_cell(change),
            )
        console.print(table)

    if outcome.alerts:
        console.print(_alerts_table(outcome.alerts))

    if outcome.skipped:
        table = Table(title="Skipped files", title_justify="left")
        table.add_column("Path", overflow="fold")
        table.add_column("Reason")
        for path, reason in outcome.skipped:
            table.add_row(path, reason)
        console.print(table)


def render_scan_no_baseline(*, json_output: bool) -> None:
    """Tell the user there is no baseline yet, in either Rich or JSON form."""
    message = "no baseline; run `codeguard init` first"
    if json_output:
        _print_json(
            {
                "ok": False,
                "error": "no_baseline",
                "message": message,
            }
        )
        return

    console = Console()
    console.print(
        Panel(
            "Run [bold]codeguard init[/bold] first to capture a baseline.",
            title="[red]\u2717 No baseline[/red]",
            title_align="left",
            border_style="red",
        )
    )
