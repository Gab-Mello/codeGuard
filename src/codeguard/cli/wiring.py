"""Composition root: builds a fully-wired MonitoringService for the CLI.

The CLI is the only place where the application layer meets concrete
infrastructure adapters. This factory keeps that wiring in one place so
each command stays a thin script.
"""

from __future__ import annotations

from pathlib import Path

from ..application import MonitoringService
from ..infrastructure.filesystem import FileScanner
from ..infrastructure.persistence import (
    BaselineRepository,
    Database,
    ScanHistoryRepository,
)
from .paths import database_path


def build_monitoring_service(project_root: Path) -> MonitoringService:
    """Wire a `MonitoringService` to its concrete infrastructure adapters.

    Each CLI invocation builds a fresh service bound to the database file
    under ``<project_root>/.codeguard/codeguard.db`` and a scanner that
    walks the project from the same root.
    """
    db = Database(database_path(project_root))
    return MonitoringService(
        baseline_repo=BaselineRepository(db),
        scan_history_repo=ScanHistoryRepository(db),
        scanner=FileScanner(),
    )
