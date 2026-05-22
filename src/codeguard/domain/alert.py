"""Severity-tagged notifications produced when sensitive files change."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from .change import ChangeType


class Severity(str, Enum):
    """Ranked severity tag carried by every alert; used for sorting and CI gating."""

    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"

    @property
    def rank(self) -> int:
        """Numeric rank for sorting (CRITICAL = highest)."""
        return _SEVERITY_RANK[self]


_SEVERITY_RANK: dict[Severity, int] = {
    Severity.LOW: 1,
    Severity.MEDIUM: 2,
    Severity.HIGH: 3,
    Severity.CRITICAL: 4,
}


@dataclass(frozen=True, slots=True)
class Alert:
    """A contextual alert raised about a specific file change.

    `rule_name` identifies which AlertRule produced the alert and is kept
    around for persistence, presentation, and debugging.
    """

    relative_path: str
    change_type: ChangeType
    severity: Severity
    rule_name: str
    message: str
