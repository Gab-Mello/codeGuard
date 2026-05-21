"""High-severity alert when database migration files are modified or deleted."""

from __future__ import annotations

from ...domain import Alert, ChangeType, FileChange, Severity
from .base import AlertRule


class MigrationRule(AlertRule):
    """Fires on changes to files inside a `migration` or `migrations` path.

    Migrations are usually append-only — modifying or deleting an existing
    one tends to indicate a destructive rewrite that may break environments
    that already applied the original. Reported at HIGH severity.
    """

    _MIGRATION_SEGMENTS = ("migration", "migrations")
    _TRIGGER_TYPES = (ChangeType.MODIFIED, ChangeType.DELETED)

    def evaluate(self, change: FileChange) -> Alert | None:
        if change.change_type not in self._TRIGGER_TYPES:
            return None
        segments = change.relative_path.split("/")
        if not any(seg in self._MIGRATION_SEGMENTS for seg in segments):
            return None
        verb = "modified" if change.change_type is ChangeType.MODIFIED else "deleted"
        return Alert(
            relative_path=change.relative_path,
            change_type=change.change_type,
            severity=Severity.HIGH,
            rule_name=self.name,
            message=(
                f"Migration file '{change.relative_path}' was {verb}. "
                "Migrations are typically append-only — verify that environments "
                "which already applied the original version will not be broken."
            ),
        )
