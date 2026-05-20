"""Abstract base class for contextual alert rules."""

from __future__ import annotations

from abc import ABC, abstractmethod

from ...domain import Alert, FileChange


class AlertRule(ABC):
    """A single rule that may produce an `Alert` for a given `FileChange`.

    Subclasses override `evaluate` with their detection logic and optionally
    `name` if they want a stable identifier different from the class name.
    Returning ``None`` means the rule does not apply to this change.
    """

    @property
    def name(self) -> str:
        return type(self).__name__

    @abstractmethod
    def evaluate(self, change: FileChange) -> Alert | None:
        """Return an `Alert` if the rule fires on `change`, otherwise ``None``."""
