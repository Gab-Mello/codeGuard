"""Application service that coordinates the file-monitoring workflow."""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from ..domain.differ import SnapshotDiffer
from ..domain.rules import AlertManager, default_rules
from ..infrastructure.filesystem import FileScanner
from ..domain import Alert, FileChange
from ..infrastructure.persistence import (
    BaselineRecord,
    BaselineRepository,
    Database,
    ScanHistoryRepository,
    ScanRecord,
)
from .ports import BaselineRepositoryProtocol, ScanHistoryRepositoryProtocol


_logger = logging.getLogger(__name__)


DB_RELATIVE_PATH: tuple[str, ...] = (".codeguard", "codeguard.db")


def _default_database_factory(project_root: Path) -> Database:
    return Database(project_root.joinpath(*DB_RELATIVE_PATH))


class BaselineAlreadyExistsError(Exception):
    """Raised when `create_baseline` is called and a baseline already exists.

    The existing record is attached so callers can render the prior
    timestamp without a second query.
    """

    def __init__(self, existing: BaselineRecord) -> None:
        super().__init__(
            f"baseline already exists (created {existing.created_at.isoformat()})"
        )
        self.existing = existing


class BaselineNotFoundError(Exception):
    """Raised when an operation requires a baseline that has not been created."""


class ScanNotFoundError(Exception):
    """Raised when an operation references a scan that does not exist.

    `scan_id` is `None` when the caller asked for the latest scan and
    no scans have been recorded yet, otherwise it carries the missing id.
    """

    def __init__(self, scan_id: int | None) -> None:
        if scan_id is None:
            super().__init__("no scans yet; run `codeguard scan` first")
        else:
            super().__init__(f"scan {scan_id} not found")
        self.scan_id = scan_id


@dataclass(slots=True, frozen=True)
class BaselineOutcome:
    """Result of `create_baseline`: the persisted record plus any skipped paths."""

    record: BaselineRecord
    skipped: list[tuple[str, str]] = field(default_factory=list)


@dataclass(slots=True, frozen=True)
class ScanOutcome:
    """Result of `scan`: the persisted record plus the changes, alerts, and skips."""

    record: ScanRecord
    changes: list[FileChange]
    alerts: list[Alert]
    skipped: list[tuple[str, str]] = field(default_factory=list)


class MonitoringService:
    """Single facade the CLI talks to.

    Wires the scanner, differ, alert manager, and repositories together so
    callers never reach into them directly. Each method takes a project
    path, resolves it, and opens the corresponding `<project>/.codeguard/
    codeguard.db` SQLite file. Collaborators are constructor-injected so
    they can be replaced or mocked in tests.
    """

    def __init__(
        self,
        *,
        scanner: FileScanner | None = None,
        differ: SnapshotDiffer | None = None,
        alert_manager: AlertManager | None = None,
        baseline_repo: BaselineRepositoryProtocol | None = None,
        scan_history_repo: ScanHistoryRepositoryProtocol | None = None,
        database_factory: Callable[[Path], Database] | None = None,
    ) -> None:
        self._scanner = scanner or FileScanner()
        self._differ = differ or SnapshotDiffer()
        self._alert_manager = alert_manager or AlertManager(default_rules())
        self._baseline_repo = baseline_repo
        self._scan_history_repo = scan_history_repo
        self._database_factory = database_factory or _default_database_factory

    def create_baseline(
        self,
        project_root: Path | str,
        *,
        force: bool = False,
    ) -> BaselineOutcome:
        """Scan `project_root` and persist its snapshot as the trusted baseline.

        With `force=False` (default), a pre-existing baseline causes
        `BaselineAlreadyExistsError` instead of being overwritten. With
        `force=True` the previous baseline (and its scans, changes, alerts)
        are cascaded away atomically before the new one is saved.
        """
        root = self._resolve(project_root)
        baseline_repo = self._baseline(root)
        if not force:
            existing = baseline_repo.find()
            if existing is not None:
                raise BaselineAlreadyExistsError(existing)
        scan = self._scanner.scan(root)
        record = baseline_repo.save(scan.snapshot)
        _logger.info(
            "baseline saved (id=%s, files=%d)",
            record.baseline_id,
            len(scan.snapshot.files),
        )
        return BaselineOutcome(record=record, skipped=list(scan.skipped))

    def scan(self, project_root: Path | str) -> ScanOutcome:
        """Scan `project_root`, diff against the baseline, and persist results.

        Raises `BaselineNotFoundError` if no baseline has been created yet.
        """
        root = self._resolve(project_root)
        baseline_repo = self._baseline(root)
        baseline = baseline_repo.find()
        if baseline is None:
            raise BaselineNotFoundError("no baseline; run `codeguard init` first")

        started_at = datetime.now(timezone.utc)
        scan = self._scanner.scan(root)
        changes = self._differ.diff(baseline.snapshot, scan.snapshot)
        alerts = self._alert_manager.evaluate(changes)
        history_repo = self._scan_history(root)
        record = history_repo.record_scan(
            baseline_id=baseline.baseline_id,
            snapshot=scan.snapshot,
            changes=changes,
            alerts=alerts,
            started_at=started_at,
        )
        _logger.info(
            "scan complete (id=%s, changes=%d, alerts=%d, critical=%d)",
            record.scan_id,
            record.change_count,
            record.alert_count,
            record.critical_count,
        )
        return ScanOutcome(
            record=record,
            changes=changes,
            alerts=alerts,
            skipped=list(scan.skipped),
        )

    def latest_baseline(self, project_root: Path | str) -> BaselineRecord | None:
        """Return the active baseline for `project_root`, or `None` if absent."""
        root = self._resolve(project_root)
        return self._baseline(root).find()

    def list_history(
        self,
        project_root: Path | str,
        *,
        limit: int | None = None,
    ) -> list[ScanRecord]:
        """Return persisted scans, newest first; empty list if no scans yet."""
        root = self._resolve(project_root)
        return self._scan_history(root).list_scans(limit=limit)

    def list_alerts(
        self,
        project_root: Path | str,
        *,
        scan_id: int | None = None,
    ) -> tuple[ScanRecord, list[Alert]]:
        """Return the alerts for a specific scan, or the latest scan by default.

        Raises `ScanNotFoundError` when `scan_id` is given but no row matches,
        or when `scan_id` is `None` and no scans exist yet.
        """
        root = self._resolve(project_root)
        history_repo = self._scan_history(root)
        if scan_id is None:
            record = history_repo.latest_scan()
            if record is None:
                raise ScanNotFoundError(None)
        else:
            record = history_repo.get_scan(scan_id)
            if record is None:
                raise ScanNotFoundError(scan_id)
        alerts = history_repo.alerts_for_scan(record.scan_id)
        return record, alerts

    def _open(self, project_root: Path | str) -> tuple[Database, Path]:
        root = Path(project_root).resolve()
        return self._database_factory(root), root

    @staticmethod
    def _resolve(project_root: Path | str) -> Path:
        return Path(project_root).resolve()

    def _baseline(self, root: Path) -> BaselineRepositoryProtocol:
        if self._baseline_repo is not None:
            return self._baseline_repo
        return BaselineRepository(self._database_factory(root))

    def _scan_history(self, root: Path) -> ScanHistoryRepositoryProtocol:
        if self._scan_history_repo is not None:
            return self._scan_history_repo
        return ScanHistoryRepository(self._database_factory(root))
