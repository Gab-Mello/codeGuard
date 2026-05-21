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
        table = Table(title="Alerts", title_justify="left")
        table.add_column("Severity", no_wrap=True)
        table.add_column("Path", overflow="fold")
        table.add_column("Rule", no_wrap=True)
        table.add_column("Message")
        for alert in _sorted_alerts(outcome.alerts):
            style = _SEVERITY_STYLE[alert.severity]
            table.add_row(
                f"[{style}]{alert.severity.value}[/{style}]",
                alert.relative_path,
                alert.rule_name,
                alert.message,
            )
        console.print(table)

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
        f"{baseline.created_at.isoformat(sep=' ')} \u00b7 "
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
            f"{latest_scan.started_at.isoformat(sep=' ')} \u00b7 "
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
