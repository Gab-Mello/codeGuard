"""Renderers shared by every CLI command: Rich for humans, JSON for scripts.

Each renderer is a free function. Human output uses `rich.console.Console`
and lands on stdout; JSON output goes through `json.dumps` and lands on
stdout too. Errors and logs are emitted on stderr by the command layer.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from ..services import (
    Alert,
    BaselineOutcome,
    BaselineRecord,
    ChangeType,
    FileChange,
    ScanOutcome,
    ScanRecord,
    Severity,
)
from .paths import database_path


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


_CHANGE_TYPE_ORDER: dict[ChangeType, int] = {
    ChangeType.CREATED: 0,
    ChangeType.MODIFIED: 1,
    ChangeType.DELETED: 2,
}

_CHANGE_TYPE_STYLE: dict[ChangeType, str] = {
    ChangeType.CREATED: "green",
    ChangeType.MODIFIED: "yellow",
    ChangeType.DELETED: "red",
}

_SEVERITY_STYLE: dict[Severity, str] = {
    Severity.CRITICAL: "bold red",
    Severity.HIGH: "yellow",
    Severity.MEDIUM: "blue",
    Severity.LOW: "dim cyan",
}


def _format_size(num_bytes: int) -> str:
    if num_bytes < 1024:
        return f"{num_bytes} B"
    if num_bytes < 1024 * 1024:
        return f"{num_bytes / 1024:.1f} KB"
    if num_bytes < 1024 * 1024 * 1024:
        return f"{num_bytes / (1024 * 1024):.1f} MB"
    return f"{num_bytes / (1024 * 1024 * 1024):.1f} GB"


def _format_relative(when: datetime) -> str:
    now = datetime.now(timezone.utc)
    target = when if when.tzinfo else when.replace(tzinfo=timezone.utc)
    delta = now - target
    seconds = int(delta.total_seconds())
    if seconds < 0:
        return "just now"
    if seconds < 60:
        return "just now"
    minutes = seconds // 60
    if minutes < 60:
        return f"{minutes} minute{'s' if minutes != 1 else ''} ago"
    hours = minutes // 60
    if hours < 24:
        return f"{hours} hour{'s' if hours != 1 else ''} ago"
    days = hours // 24
    if days < 30:
        return f"{days} day{'s' if days != 1 else ''} ago"
    months = days // 30
    if months < 12:
        return f"{months} month{'s' if months != 1 else ''} ago"
    years = days // 365
    return f"{years} year{'s' if years != 1 else ''} ago"


def _change_size_cell(change: FileChange) -> str:
    if change.change_type is ChangeType.CREATED:
        return _format_size(change.after.size_bytes)  # type: ignore[union-attr]
    if change.change_type is ChangeType.DELETED:
        return _format_size(change.before.size_bytes)  # type: ignore[union-attr]
    before = _format_size(change.before.size_bytes)  # type: ignore[union-attr]
    after = _format_size(change.after.size_bytes)  # type: ignore[union-attr]
    return f"{before} \u2192 {after}"


def _change_to_json(change: FileChange) -> dict:
    before = change.before
    after = change.after
    return {
        "relative_path": change.relative_path,
        "change_type": change.change_type.value,
        "before_size": before.size_bytes if before else None,
        "after_size": after.size_bytes if after else None,
        "before_sha256": before.sha256 if before else None,
        "after_sha256": after.sha256 if after else None,
    }


def _alert_to_json(alert: Alert) -> dict:
    return {
        "relative_path": alert.relative_path,
        "change_type": alert.change_type.value,
        "severity": alert.severity.value,
        "rule_name": alert.rule_name,
        "message": alert.message,
    }


def _sorted_changes(changes: list[FileChange]) -> list[FileChange]:
    return sorted(
        changes,
        key=lambda c: (_CHANGE_TYPE_ORDER[c.change_type], c.relative_path),
    )


def _sorted_alerts(alerts: list[Alert]) -> list[Alert]:
    return sorted(
        alerts,
        key=lambda a: (-a.severity.rank, a.relative_path),
    )


def _alerts_table(alerts: list[Alert], *, title: str = "Alerts") -> Table:
    table = Table(title=title, title_justify="left")
    table.add_column("Severity", no_wrap=True)
    table.add_column("Path", overflow="fold")
    table.add_column("Rule", no_wrap=True)
    table.add_column("Message")
    for alert in _sorted_alerts(alerts):
        style = _SEVERITY_STYLE[alert.severity]
        table.add_row(
            f"[{style}]{alert.severity.value}[/{style}]",
            alert.relative_path,
            alert.rule_name,
            alert.message,
        )
    return table


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


def _scan_record_to_json(record: ScanRecord) -> dict:
    duration_ms = int((record.finished_at - record.started_at).total_seconds() * 1000)
    return {
        "scan_id": record.scan_id,
        "started_at": record.started_at,
        "finished_at": record.finished_at,
        "duration_ms": duration_ms,
        "change_count": record.change_count,
        "alert_count": record.alert_count,
        "critical_count": record.critical_count,
    }


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
