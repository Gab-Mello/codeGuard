"""Extensible alert rule engine: an abstract rule and a polymorphic manager."""

from .base import AlertRule
from .manager import AlertManager

__all__ = ["AlertRule", "AlertManager"]
