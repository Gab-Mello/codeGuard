"""Critical alert when a `.env` file is modified or deleted."""

from __future__ import annotations

from posixpath import basename

from ...domain import Alert, ChangeType, FileChange, Severity
from .base import AlertRule


class EnvFileRule(AlertRule):
    """Fires on any change to a `.env` (or `.env.<variant>`) file.

    `.env` files typically hold secrets and per-environment configuration,
    so any creation, modification, or deletion is treated as CRITICAL —
    a deliberate review is needed before accepting the change.
    """

    _VERBS: dict[ChangeType, str] = {
        ChangeType.CREATED: "created",
        ChangeType.MODIFIED: "modified",
        ChangeType.DELETED: "deleted",
    }

    def evaluate(self, change: FileChange) -> Alert | None:
        name = basename(change.relative_path)
        if not (name == ".env" or name.startswith(".env.")):
            return None
        verb = self._VERBS[change.change_type]
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
