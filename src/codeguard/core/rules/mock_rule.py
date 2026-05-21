"""Medium-severity alert when generated mock files are modified."""

from __future__ import annotations

import fnmatch
from posixpath import basename

from ...domain import Alert, ChangeType, FileChange, Severity
from .base import AlertRule


class MockFileRule(AlertRule):
    """Fires on modifications to generated mock files.

    Matches Go-style mock conventions (`mock_*.go`, `*_mock.go`) and any
    file inside a `mocks/` directory. Generated mocks should normally be
    regenerated from their source interface — a hand edit, or a stale
    regeneration, is the kind of mistake worth surfacing.
    """

    _BASENAME_PATTERNS = ("mock_*.go", "*_mock.go")
    _MOCK_DIR_SEGMENT = "mocks"

    def evaluate(self, change: FileChange) -> Alert | None:
        if change.change_type is not ChangeType.MODIFIED:
            return None
        if not self._matches(change.relative_path):
            return None
        return Alert(
            relative_path=change.relative_path,
            change_type=change.change_type,
            severity=Severity.MEDIUM,
            rule_name=self.name,
            message=(
                f"Mock file '{change.relative_path}' was modified. "
                "Verify whether it was regenerated correctly from its source "
                "interface, rather than edited by hand."
            ),
        )

    def _matches(self, relative_path: str) -> bool:
        segments = relative_path.split("/")
        if any(seg == self._MOCK_DIR_SEGMENT for seg in segments[:-1]):
            return True
        name = basename(relative_path)
        return any(fnmatch.fnmatchcase(name, pat) for pat in self._BASENAME_PATTERNS)
