"""High-severity alert when Docker build or compose files are modified."""

from __future__ import annotations

from posixpath import basename

from ...domain import Alert, ChangeType, FileChange, Severity
from .base import AlertRule


class DockerFileRule(AlertRule):
    """Fires on modifications to Dockerfiles and docker-compose manifests.

    These files define how the project is built and orchestrated; an
    unexpected edit can change runtime behavior, exposed ports, or image
    contents in subtle ways. Reported at HIGH severity.
    """

    DOCKER_FILES: frozenset[str] = frozenset({
        "Dockerfile",
        "docker-compose.yml",
        "docker-compose.yaml",
    })

    def evaluate(self, change: FileChange) -> Alert | None:
        if change.change_type is not ChangeType.MODIFIED:
            return None
        if basename(change.relative_path) not in self.DOCKER_FILES:
            return None
        return Alert(
            relative_path=change.relative_path,
            change_type=change.change_type,
            severity=Severity.HIGH,
            rule_name=self.name,
            message=(
                f"Container configuration '{change.relative_path}' was modified. "
                "Review the diff for changes to base images, exposed ports, or "
                "build steps before rebuilding or deploying."
            ),
        )
