"""Renderers for `codeguard alerts`: per-scan alert view + scan-not-found error."""

from __future__ import annotations

from rich.console import Console
from rich.panel import Panel

from ...services import Alert, ScanRecord, Severity
from ._shared import _alert_to_json, _alerts_table, _print_json, _sorted_alerts


def render_alerts_view(
    record: ScanRecord,
    alerts: list[Alert],
    *,
    severity_filter: Severity | None,
    json_output: bool,
) -> None:
    """Show the alerts persisted for a single scan, optionally filtered."""
    total_unfiltered = record.alert_count
    visible = (
        [a for a in alerts if a.severity is severity_filter]
        if severity_filter is not None
        else list(alerts)
    )

    if json_output:
        payload: dict = {
            "ok": True,
            "scan_id": record.scan_id,
            "started_at": record.started_at,
            "finished_at": record.finished_at,
            "alert_count": total_unfiltered,
            "critical_count": record.critical_count,
            "filter": (
                {"severity": severity_filter.value}
                if severity_filter is not None
                else None
            ),
            "alerts": [_alert_to_json(a) for a in _sorted_alerts(visible)],
        }
        if severity_filter is not None:
            payload["total_unfiltered"] = total_unfiltered
        _print_json(payload)
        return

    console = Console()
    critical_segment = (
        f"[bold red]{record.critical_count} critical[/bold red]"
        if record.critical_count > 0
        else f"[dim]{record.critical_count} critical[/dim]"
    )
    console.print(
        f"[bold]Alerts for scan #{record.scan_id}[/bold] \u00b7 "
        f"{record.started_at.isoformat(sep=' ')} \u00b7 "
        f"{total_unfiltered} total \u00b7 "
        f"{critical_segment}"
    )

    if not visible:
        if severity_filter is not None and total_unfiltered > 0:
            console.print(
                f"[dim](no alerts at severity {severity_filter.value})[/dim]"
            )
        else:
            console.print("[dim](no alerts)[/dim]")
        return

    title = "Alerts"
    if severity_filter is not None:
        title = f"Alerts (filtered to {severity_filter.value})"
    console.print(_alerts_table(visible, title=title))


def render_scan_not_found(scan_id: int | None, *, json_output: bool) -> None:
    """Tell the user the requested scan does not exist."""
    if json_output:
        if scan_id is None:
            _print_json({"ok": False, "error": "no_scans"})
        else:
            _print_json(
                {"ok": False, "error": "scan_not_found", "scan_id": scan_id}
            )
        return

    console = Console()
    if scan_id is None:
        console.print(
            Panel(
                "Run [bold]codeguard scan[/bold] first to record a scan.",
                title="[red]\u2717 No scans yet[/red]",
                title_align="left",
                border_style="red",
            )
        )
    else:
        console.print(
            Panel(
                f"No scan with id [bold]{scan_id}[/bold] exists in the history.",
                title=f"[red]\u2717 Scan {scan_id} not found[/red]",
                title_align="left",
                border_style="red",
            )
        )
