"""Application service that coordinates the file monitoring workflow."""

from __future__ import annotations

from pathlib import Path

from ..core.scanner import FileScanner, ScanResult


class MonitoringService:
    """Coordinates scanning, baseline creation, change detection, and alerts.

    The GUI talks only to this service; it never reaches into the scanner,
    hasher, or repositories directly. Collaborators are constructor-injected
    so they can be swapped or mocked.
    """

    def __init__(self, scanner: FileScanner | None = None) -> None:
        self._scanner = scanner or FileScanner()

    @property
    def scanner(self) -> FileScanner:
        return self._scanner

    def create_baseline(self, project_root: Path | str) -> ScanResult:
        """Scan `project_root` and return its trusted baseline state."""
        return self._scanner.scan(project_root)
