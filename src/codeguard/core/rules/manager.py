"""Aggregator that runs every registered alert rule against a change set."""

from __future__ import annotations

from collections.abc import Iterable

from ...domain import Alert, FileChange
from .base import AlertRule


class AlertManager:
    """Holds a collection of `AlertRule`s and dispatches changes to each.

    Polymorphism is the point of this class: rules implement a shared
    `evaluate` contract, and the manager treats every concrete rule
    interchangeably without knowing which one it is.
    """

    def __init__(self, rules: Iterable[AlertRule] | None = None) -> None:
        self._rules: list[AlertRule] = list(rules) if rules else []

    @property
    def rules(self) -> tuple[AlertRule, ...]:
        return tuple(self._rules)

    def register(self, rule: AlertRule) -> None:
        self._rules.append(rule)

    def evaluate(self, changes: Iterable[FileChange]) -> list[Alert]:
        """Return all alerts produced by the registered rules for `changes`.

        Output is sorted by severity (highest first) and then by path, so
        renderers display the most urgent alerts first in a stable order.
        """
        alerts: list[Alert] = []
        for change in changes:
            for rule in self._rules:
                alert = rule.evaluate(change)
                if alert is not None:
                    alerts.append(alert)
        alerts.sort(key=lambda a: (-a.severity.rank, a.relative_path))
        return alerts
