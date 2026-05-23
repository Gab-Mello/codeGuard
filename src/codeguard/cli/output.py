"""All CLI renderers in one file: plain prints for layout, Rich for color."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from rich.console import Console
from rich.panel import Panel

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


_SEVERITY_STYLE: dict[Severity, str] = {
    Severity.CRITICAL: "bold red",
    Severity.HIGH: "yellow",
    Severity.MEDIUM: "blue",
    Severity.LOW: "dim cyan",
}

_CHANGE_TYPE_STYLE: dict[ChangeType, str] = {
    ChangeType.CREATED: "green",
    ChangeType.MODIFIED: "yellow",
    ChangeType.DELETED: "red",
}

_CHANGE_TYPE_ORDER: dict[ChangeType, int] = {
    ChangeType.CREATED: 0,
    ChangeType.MODIFIED: 1,
    ChangeType.DELETED: 2,
}


def _print_json(payload: dict) -> None:
    print(json.dumps(payload, default=_json_default, indent=2))


def _json_default(value: object) -> str:
    if isinstance(value, datetime):
        return value.isoformat()
    return str(value)


def _change_dict(change: FileChange) -> dict:
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


def _alert_dict(alert: Alert) -> dict:
    return {
        "relative_path": alert.relative_path,
        "change_type": alert.change_type.value,
        "severity": alert.severity.value,
        "rule_name": alert.rule_name,
        "message": alert.message,
    }


def _scan_record_dict(record: ScanRecord) -> dict:
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


def _sorted_changes(changes: list[FileChange]) -> list[FileChange]:
    return sorted(
        changes,
        key=lambda c: (_CHANGE_TYPE_ORDER[c.change_type], c.relative_path),
    )


def _sorted_alerts(alerts: list[Alert]) -> list[Alert]:
    return sorted(alerts, key=lambda a: (-a.severity.rank, a.relative_path))


def _print_alerts(console: Console, alerts: list[Alert]) -> None:
    for alert in _sorted_alerts(alerts):
        style = _SEVERITY_STYLE[alert.severity]
        console.print(
            f"  [{style}]{alert.severity.value}[/{style}] "
            f"{alert.relative_path} \u2014 {alert.message}"
        )


def _print_changes(console: Console, changes: list[FileChange]) -> None:
    for change in _sorted_changes(changes):
        style = _CHANGE_TYPE_STYLE[change.change_type]
        console.print(
            f"  [{style}]{change.change_type.value}[/{style}] {change.relative_path}"
        )


def render_baseline_created(outcome: BaselineOutcome, *, json_output: bool) -> None:
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
    console.print("[bold green]Baseline saved[/bold green]")
    console.print(f"  Project:  {snapshot.project_root}")
    console.print(f"  Files:    {len(snapshot.files)}")
    console.print(f"  Created:  {record.created_at.isoformat(sep=' ')}")
    console.print(f"  Database: {db_path}")
    console.print()
    console.print("[dim]Next: run `codeguard scan` to detect changes.[/dim]")
    if outcome.skipped:
        console.print()
        console.print("Skipped files:")
        for path, reason in outcome.skipped:
            console.print(f"  {path} \u2014 {reason}")


def render_baseline_already_exists(existing: BaselineRecord, *, json_output: bool) -> None:
    """Show the existing-baseline error in either Rich or JSON form."""
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
        f"Created: {existing.created_at.isoformat(sep=' ')}\n"
        "Use --force to re-baseline."
    )
    console.print(
        Panel(
            body,
            title="[red]Baseline already exists[/red]",
            title_align="left",
            border_style="red",
        )
    )


def render_scan_result(outcome: ScanOutcome, *, json_output: bool) -> None:
    """Show the scan summary, changes, and alerts on stdout."""
    record = outcome.record
    duration_ms = int((record.finished_at - record.started_at).total_seconds() * 1000)

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
                "changes": [_change_dict(c) for c in outcome.changes],
                "alerts": [_alert_dict(a) for a in outcome.alerts],
                "skipped": [list(item) for item in outcome.skipped],
            }
        )
        return

    console = Console()
    crit = record.critical_count
    crit_str = f"[bold red]{crit} critical[/bold red]" if crit > 0 else f"[dim]{crit} critical[/dim]"
    console.print(
        f"[bold]Scan #{record.scan_id}[/bold] \u00b7 "
        f"{record.change_count} changes \u00b7 "
        f"{record.alert_count} alerts \u00b7 "
        f"{crit_str} \u00b7 {duration_ms} ms"
    )
    if outcome.changes:
        console.print()
        console.print("Changes:")
        _print_changes(console, outcome.changes)
    if outcome.alerts:
        console.print()
        console.print("Alerts:")
        _print_alerts(console, outcome.alerts)
    if outcome.skipped:
        console.print()
        console.print("Skipped files:")
        for path, reason in outcome.skipped:
            console.print(f"  {path} \u2014 {reason}")


def render_scan_no_baseline(*, json_output: bool) -> None:
    """Tell the user there is no baseline yet."""
    if json_output:
        _print_json(
            {
                "ok": False,
                "error": "no_baseline",
                "message": "no baseline; run `codeguard init` first",
            }
        )
        return

    Console().print(
        Panel(
            "Run `codeguard init` first to capture a baseline.",
            title="[red]No baseline[/red]",
            title_align="left",
            border_style="red",
        )
    )


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
                    _scan_record_dict(latest_scan) if latest_scan else None
                ),
                "clean": (
                    None if latest_scan is None else latest_scan.change_count == 0
                ),
            }
        )
        return

    if latest_scan is None:
        header = "[blue]Baseline ready (no scans yet)[/blue]"
    elif latest_scan.change_count == 0:
        header = "[green]Clean[/green]"
    else:
        header = "[yellow]Changes detected[/yellow]"

    console = Console()
    console.print(f"[bold]Status[/bold] \u00b7 {header}")
    console.print(f"  Project:   {project_root}")
    console.print(f"  Database:  {db_path}")
    console.print(
        f"  Baseline:  #{baseline.baseline_id} \u00b7 "
        f"{baseline.created_at.isoformat(sep=' ')} \u00b7 "
        f"{len(baseline.snapshot.files)} files"
    )
    if latest_scan is None:
        console.print("  Last scan: (no scans yet)")
    else:
        duration_ms = int(
            (latest_scan.finished_at - latest_scan.started_at).total_seconds() * 1000
        )
        console.print(
            f"  Last scan: #{latest_scan.scan_id} \u00b7 "
            f"{latest_scan.started_at.isoformat(sep=' ')} \u00b7 "
            f"{latest_scan.change_count} changes \u00b7 "
            f"{latest_scan.critical_count} critical \u00b7 "
            f"{duration_ms} ms"
        )


def render_history(
    project_root: str,
    records: list[ScanRecord],
    *,
    limit: int | None,
    json_output: bool,
) -> None:
    """Show persisted scans newest-first."""
    if json_output:
        _print_json(
            {
                "ok": True,
                "project_root": project_root,
                "scan_count": len(records),
                "limit": limit,
                "scans": [_scan_record_dict(r) for r in records],
            }
        )
        return

    console = Console()
    header = f"[bold]Scan history[/bold] \u00b7 {len(records)} scans"
    if limit is not None:
        header += f" \u00b7 limit {limit}"
    console.print(header)
    if not records:
        console.print("  [dim](no scans yet)[/dim]")
        return
    for r in records:
        duration_ms = int((r.finished_at - r.started_at).total_seconds() * 1000)
        crit = (
            f"[bold red]{r.critical_count} critical[/bold red]"
            if r.critical_count > 0
            else f"[dim]{r.critical_count} critical[/dim]"
        )
        console.print(
            f"  #{r.scan_id} \u00b7 {r.started_at.isoformat(sep=' ')} \u00b7 "
            f"{r.change_count} changes \u00b7 {r.alert_count} alerts \u00b7 "
            f"{crit} \u00b7 {duration_ms} ms"
        )


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
            "alerts": [_alert_dict(a) for a in _sorted_alerts(visible)],
        }
        if severity_filter is not None:
            payload["total_unfiltered"] = total_unfiltered
        _print_json(payload)
        return

    console = Console()
    crit = record.critical_count
    crit_str = (
        f"[bold red]{crit} critical[/bold red]" if crit > 0 else f"[dim]{crit} critical[/dim]"
    )
    console.print(
        f"[bold]Alerts for scan #{record.scan_id}[/bold] \u00b7 "
        f"{record.started_at.isoformat(sep=' ')} \u00b7 "
        f"{total_unfiltered} total \u00b7 {crit_str}"
    )
    if not visible:
        if severity_filter is not None and total_unfiltered > 0:
            console.print(f"  [dim](no alerts at severity {severity_filter.value})[/dim]")
        else:
            console.print("  [dim](no alerts)[/dim]")
        return
    if severity_filter is not None:
        console.print(f"[dim](filtered to {severity_filter.value})[/dim]")
    _print_alerts(console, visible)


def render_scan_not_found(scan_id: int | None, *, json_output: bool) -> None:
    """Tell the user the requested scan does not exist."""
    if json_output:
        if scan_id is None:
            _print_json({"ok": False, "error": "no_scans"})
        else:
            _print_json({"ok": False, "error": "scan_not_found", "scan_id": scan_id})
        return

    console = Console()
    if scan_id is None:
        console.print(
            Panel(
                "Run `codeguard scan` first to record a scan.",
                title="[red]No scans yet[/red]",
                title_align="left",
                border_style="red",
            )
        )
    else:
        console.print(
            Panel(
                f"No scan with id {scan_id} exists in the history.",
                title=f"[red]Scan {scan_id} not found[/red]",
                title_align="left",
                border_style="red",
            )
        )


def render_review_summary(outcome: ScanOutcome, *, top: int, json_output: bool) -> None:
    """Render a prioritised, action-oriented view of the latest scan."""
    record = outcome.record
    duration_ms = int((record.finished_at - record.started_at).total_seconds() * 1000)

    counts = {ChangeType.CREATED: 0, ChangeType.MODIFIED: 0, ChangeType.DELETED: 0}
    for c in outcome.changes:
        counts[c.change_type] += 1

    if record.critical_count > 0:
        next_steps = [
            "Run `git diff` on each CRITICAL file before committing.",
            "If these changes are expected, run `codeguard init --force` to update the baseline.",
        ]
    elif record.alert_count > 0:
        next_steps = [
            "Review the alerts above; consider `codeguard alerts --severity HIGH` for the full list.",
            "If these changes are expected, run `codeguard init --force` to update the baseline.",
        ]
    elif record.change_count > 0:
        next_steps = [
            "No alerts fired, but files changed. If expected, run `codeguard init --force`.",
        ]
    else:
        next_steps = ["Project matches baseline \u2014 no action needed."]

    sorted_alerts = _sorted_alerts(outcome.alerts)
    sorted_changes = _sorted_changes(outcome.changes)
    using_alerts = bool(sorted_alerts)
    if using_alerts:
        visible_alerts = sorted_alerts[:top]
        review_truncated = len(sorted_alerts) > top
        remaining = len(sorted_alerts) - len(visible_alerts)
    else:
        visible_changes = sorted_changes[:top]
        review_truncated = len(sorted_changes) > top
        remaining = len(sorted_changes) - len(visible_changes)

    if json_output:
        if using_alerts:
            review_payload = [
                {
                    "rank": i + 1,
                    "kind": "alert",
                    "severity": a.severity.value,
                    "relative_path": a.relative_path,
                    "change_type": a.change_type.value,
                    "rule_name": a.rule_name,
                    "message": a.message,
                }
                for i, a in enumerate(visible_alerts)
            ]
        else:
            review_payload = [
                {
                    "rank": i + 1,
                    "kind": "change",
                    "relative_path": c.relative_path,
                    "change_type": c.change_type.value,
                }
                for i, c in enumerate(visible_changes)
            ]
        _print_json(
            {
                "ok": True,
                "scan_id": record.scan_id,
                "summary": {
                    "change_count": record.change_count,
                    "created_count": counts[ChangeType.CREATED],
                    "modified_count": counts[ChangeType.MODIFIED],
                    "deleted_count": counts[ChangeType.DELETED],
                    "alert_count": record.alert_count,
                    "critical_count": record.critical_count,
                    "duration_ms": duration_ms,
                },
                "review": review_payload,
                "review_truncated": review_truncated,
                "next_steps": next_steps,
            }
        )
        return

    console = Console()
    crit = record.critical_count
    crit_str = (
        f"[bold red]{crit} critical[/bold red]" if crit > 0 else f"[dim]{crit} critical[/dim]"
    )
    console.print(f"[bold]CodeGuard Review[/bold] \u00b7 Scan #{record.scan_id}")
    console.print()
    console.print("Summary:")
    console.print(
        f"  {record.change_count} changes "
        f"({counts[ChangeType.CREATED]} created, "
        f"{counts[ChangeType.MODIFIED]} modified, "
        f"{counts[ChangeType.DELETED]} deleted) \u00b7 "
        f"{record.alert_count} alerts \u00b7 {crit_str} \u00b7 {duration_ms} ms"
    )
    console.print()

    if using_alerts and visible_alerts:
        console.print("Review first:")
        for i, alert in enumerate(visible_alerts, start=1):
            style = _SEVERITY_STYLE[alert.severity]
            console.print(
                f"  {i}. [{style}]{alert.severity.value}[/{style}] "
                f"{alert.relative_path} \u00b7 [dim]{alert.rule_name}[/dim]"
            )
            console.print(f"     {alert.message}")
        if review_truncated:
            console.print(
                f"  [dim](\u2026 and {remaining} more \u2014 run `codeguard alerts` to see all)[/dim]"
            )
        console.print()
    elif not using_alerts and visible_changes:
        console.print("Changed files:")
        for i, change in enumerate(visible_changes, start=1):
            style = _CHANGE_TYPE_STYLE[change.change_type]
            console.print(
                f"  {i}. [{style}]{change.change_type.value}[/{style}] {change.relative_path}"
            )
        if review_truncated:
            console.print(
                f"  [dim](\u2026 and {remaining} more \u2014 run `codeguard scan` to see all)[/dim]"
            )
        console.print()

    console.print("Suggested next steps:")
    for step in next_steps:
        console.print(f"  \u2022 {step}")
