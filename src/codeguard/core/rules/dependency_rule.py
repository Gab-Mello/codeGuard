"""High-severity alert when a project dependency manifest is modified."""

from __future__ import annotations

from posixpath import basename

from ...domain import Alert, ChangeType, FileChange, Severity
from .base import AlertRule


class DependencyFileRule(AlertRule):
    """Fires on modifications to common dependency manifests.

    A silent change to a manifest can pull in unexpected packages or
    versions, so any modification is reported at HIGH severity. Creation
    and deletion are intentionally not flagged here — adding or removing
    a manifest is usually a deliberate project-level decision.
    """

    DEPENDENCY_FILES: frozenset[str] = frozenset({
        "requirements.txt",
        "pyproject.toml",
        "package.json",
        "go.mod",
        "go.sum",
    })

    def evaluate(self, change: FileChange) -> Alert | None:
        if change.change_type is not ChangeType.MODIFIED:
            return None
        if basename(change.relative_path) not in self.DEPENDENCY_FILES:
            return None
        return Alert(
            relative_path=change.relative_path,
            change_type=change.change_type,
            severity=Severity.HIGH,
            rule_name=self.name,
            message=(
                f"Dependency manifest '{change.relative_path}' was modified. "
                "Confirm that any added, removed, or upgraded packages are "
                "intentional and review their changelogs."
            ),
        )
