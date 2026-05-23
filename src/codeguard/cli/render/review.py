"""Renderer for `codeguard review`: prioritised, action-oriented scan view."""

from __future__ import annotations

from rich.console import Console

from ...services import ChangeType, FileChange, ScanOutcome, ScanRecord
from ._shared import (
    _CHANGE_TYPE_STYLE,
    _SEVERITY_STYLE,
    _print_json,
    _sorted_alerts,
    _sorted_changes,
)


def _count_by_change_type(changes: list[FileChange]) -> dict[ChangeType, int]:
    counts: dict[ChangeType, int] = {
        ChangeType.CREATED: 0,
        ChangeType.MODIFIED: 0,
        ChangeType.DELETED: 0,
    }
    for change in changes:
        counts[change.change_type] += 1
    return counts


def _next_steps(record: ScanRecord) -> list[str]:
    if record.critical_count > 0:
        return [
            "Run `git diff` on each CRITICAL file before committing.",
            "If these changes are expected, run `codeguard init --force` to update the baseline.",
        ]
    if record.alert_count > 0:
        return [
            "Review the alerts above; consider `codeguard alerts --severity HIGH` for the full list.",
            "If these changes are expected, run `codeguard init --force` to update the baseline.",
        ]
    if record.change_count > 0:
        return [
            "No alerts fired, but files changed. If expected, run `codeguard init --force`.",
        ]
    return ["Project matches baseline \u2014 no action needed."]


def render_review_summary(
    outcome: ScanOutcome,
    *,
    top: int,
    json_output: bool,
) -> None:
    """Render a prioritised, action-oriented view of the latest scan."""
    record = outcome.record
    duration_ms = int(
        (record.finished_at - record.started_at).total_seconds() * 1000
    )
    counts = _count_by_change_type(outcome.changes)
    next_steps = _next_steps(record)

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
    console.print(f"[bold]CodeGuard Review[/bold] \u00b7 Scan #{record.scan_id}")
    console.print()
    critical_segment = (
        f"[bold red]{record.critical_count} critical[/bold red]"
        if record.critical_count > 0
        else f"[dim]{record.critical_count} critical[/dim]"
    )
    console.print("[bold]Summary:[/bold]")
    console.print(
        f"  {record.change_count} changes "
        f"({counts[ChangeType.CREATED]} created, "
        f"{counts[ChangeType.MODIFIED]} modified, "
        f"{counts[ChangeType.DELETED]} deleted) \u00b7 "
        f"{record.alert_count} alerts \u00b7 "
        f"{critical_segment} \u00b7 "
        f"{duration_ms} ms"
    )
    console.print()

    if using_alerts and visible_alerts:
        console.print("[bold]Review first:[/bold]")
        for i, alert in enumerate(visible_alerts, start=1):
            style = _SEVERITY_STYLE[alert.severity]
            console.print(
                f"  {i}. [{style}]{alert.severity.value:<8}[/{style}] "
                f"[bold]{alert.relative_path}[/bold] \u00b7 "
                f"[dim]{alert.rule_name}[/dim]"
            )
            console.print(f"     {alert.message}")
        if review_truncated:
            console.print(
                f"  [dim](\u2026 and {remaining} more \u2014 "
                f"run `codeguard alerts` to see all)[/dim]"
            )
        console.print()
    elif not using_alerts and visible_changes:
        console.print("[bold]Changed files:[/bold]")
        for i, change in enumerate(visible_changes, start=1):
            style = _CHANGE_TYPE_STYLE[change.change_type]
            console.print(
                f"  {i}. [{style}]{change.change_type.value:<8}[/{style}] "
                f"[bold]{change.relative_path}[/bold]"
            )
        if review_truncated:
            console.print(
                f"  [dim](\u2026 and {remaining} more \u2014 "
                f"run `codeguard scan` to see all)[/dim]"
            )
        console.print()

    console.print("[bold]Suggested next steps:[/bold]")
    for step in next_steps:
        console.print(f"  \u2022 {step}")
