"""Critical alert when a `.env` file is modified or deleted."""

from __future__ import annotations

from posixpath import basename

from ...domain import Alert, ChangeType, FileChange, Severity
from .base import AlertRule


class EnvFileRule(AlertRule):
    """Fires on changes to `.env` (or `.env.<variant>`) files.

    `.env` files typically hold secrets and per-environment configuration,
    so any modification or deletion is treated as CRITICAL — most likely
    a deliberate review is needed before accepting the change.
    """

    _TRIGGER_TYPES = (ChangeType.MODIFIED, ChangeType.DELETED)

    def evaluate(self, change: FileChange) -> Alert | None:
        if change.change_type not in self._TRIGGER_TYPES:
            return None
        name = basename(change.relative_path)
        if not (name == ".env" or name.startswith(".env.")):
            return None
        verb = "modified" if change.change_type is ChangeType.MODIFIED else "deleted"
        return Alert(
            relative_path=change.relative_path,
            change_type=change.change_type,
            severity=Severity.CRITICAL,
            rule_name=self.name,
            message=(
                f"Environment file '{change.relative_path}' was {verb}. "
                "These files often contain secrets or environment-specific "
                "configuration — review the change carefully before accepting it."
            ),
        )
