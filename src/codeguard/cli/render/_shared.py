"""Shared helpers for the CLI renderers: JSON, formatting, sorting, tables."""

from __future__ import annotations

import json
from datetime import datetime, timezone

from rich.table import Table

from ...services import Alert, ChangeType, FileChange, ScanRecord, Severity


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


def _json_default(value: object) -> str:
    if isinstance(value, datetime):
        return value.isoformat()
    return str(value)


def _print_json(payload: dict) -> None:
    print(json.dumps(payload, default=_json_default, indent=2))


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
