"""Repository protocols the application layer depends on.

These structural-typing seams (`typing.Protocol`) describe the persistence
surface `MonitoringService` needs without naming any concrete adapter. The
SQLite-backed repositories in :mod:`codeguard.infrastructure.persistence`
satisfy them implicitly — no inheritance required — and tests can supply
in-memory fakes the same way.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Iterable, Protocol

from ..domain import Alert, FileChange, Snapshot
from .dto import BaselineRecord, ScanRecord, ScanResult


class BaselineRepositoryProtocol(Protocol):
    """Persist and retrieve the trusted baseline of a project."""

    def save(self, snapshot: Snapshot) -> BaselineRecord: ...

    def find(self) -> BaselineRecord | None: ...


class ScanHistoryRepositoryProtocol(Protocol):
    """Persist scans, then retrieve them and their alerts."""

    def record_scan(
        self,
        *,
        baseline_id: int,
        snapshot: Snapshot,
        changes: Iterable[FileChange],
        alerts: Iterable[Alert],
        started_at: datetime,
        finished_at: datetime | None = None,
    ) -> ScanRecord: ...

    def list_scans(self, *, limit: int | None = None) -> list[ScanRecord]: ...

    def latest_scan(self) -> ScanRecord | None: ...

    def get_scan(self, scan_id: int) -> ScanRecord | None: ...

    def alerts_for_scan(self, scan_id: int) -> list[Alert]: ...


class FileScannerProtocol(Protocol):
    """Walk a project directory and produce a snapshot of its files."""

    def scan(self, project_root: Path | str) -> ScanResult: ...
