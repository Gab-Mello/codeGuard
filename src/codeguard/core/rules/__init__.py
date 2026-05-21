"""Extensible alert rule engine: an abstract rule and a polymorphic manager."""

from .base import AlertRule
from .dependency_rule import DependencyFileRule
from .docker_rule import DockerFileRule
from .env_rule import EnvFileRule
from .manager import AlertManager
from .migration_rule import MigrationRule
from .mock_rule import MockFileRule


def default_rules() -> list[AlertRule]:
    """Return the standard contextual rule set bundled with CodeGuard."""
    return [
        EnvFileRule(),
        DependencyFileRule(),
        DockerFileRule(),
        MigrationRule(),
        MockFileRule(),
    ]


__all__ = [
    "AlertManager",
    "AlertRule",
    "DependencyFileRule",
    "DockerFileRule",
    "EnvFileRule",
    "MigrationRule",
    "MockFileRule",
    "default_rules",
]
