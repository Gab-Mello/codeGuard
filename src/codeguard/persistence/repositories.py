"""Repository pattern: SQL stays here, domain stays in domain/."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

from ..domain import (
    Alert,
    ChangeType,
    FileChange,
    FileMetadata,
    Severity,
    Snapshot,
)
from .database import Database


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _parse_iso(value: str) -> datetime:
    return datetime.fromisoformat(value)


def _normalize_root(project_root: Path | str) -> str:
    return str(Path(project_root).resolve())


@dataclass(slots=True)
class BaselineRecord:
    """Stored baseline plus its captured snapshot."""

    baseline_id: int
    project_root: str
    created_at: datetime
    snapshot: Snapshot


@dataclass(slots=True)
class ScanRecord:
    """Summary row for one persisted scan."""

    scan_id: int
    baseline_id: int
    project_root: str
    started_at: datetime
    finished_at: datetime
    change_count: int
    alert_count: int
    critical_count: int


class _SnapshotWriter:
    """Internal helper that persists a Snapshot and its FileMetadata rows."""

    @staticmethod
    def insert(conn: sqlite3.Connection, snapshot: Snapshot) -> int:
        created_at = snapshot.created_at.isoformat()
        cursor = conn.execute(
            "INSERT INTO snapshots(project_root, created_at) VALUES (?, ?)",
            (snapshot.project_root, created_at),
        )
        snapshot_id = int(cursor.lastrowid)
        if snapshot.files:
            conn.executemany(
                """
                INSERT INTO file_metadata(
                    snapshot_id, relative_path, size_bytes, modified_at, sha256
                ) VALUES (?, ?, ?, ?, ?)
                """,
                [
                    (
                        snapshot_id,
                        meta.relative_path,
                        meta.size_bytes,
                        meta.modified_at,
                        meta.sha256,
                    )
                    for meta in snapshot.files.values()
                ],
            )
        snapshot.snapshot_id = snapshot_id
        return snapshot_id

    @staticmethod
    def load(conn: sqlite3.Connection, snapshot_id: int) -> Snapshot:
        row = conn.execute(
            "SELECT id, project_root, created_at FROM snapshots WHERE id = ?",
            (snapshot_id,),
        ).fetchone()
        if row is None:
            raise LookupError(f"Snapshot {snapshot_id} not found")
        snapshot = Snapshot(
            project_root=row["project_root"],
            created_at=_parse_iso(row["created_at"]),
            snapshot_id=int(row["id"]),
        )
        files = conn.execute(
            """
            SELECT relative_path, size_bytes, modified_at, sha256
              FROM file_metadata
             WHERE snapshot_id = ?
            """,
            (snapshot_id,),
        ).fetchall()
        for f in files:
            snapshot.add(
                FileMetadata(
                    relative_path=f["relative_path"],
                    size_bytes=int(f["size_bytes"]),
                    modified_at=float(f["modified_at"]),
                    sha256=f["sha256"],
                )
            )
        return snapshot


class BaselineRepository:
    """Persist and retrieve the trusted baseline of a project.

    Each project root has at most one active baseline; saving a new one
    replaces the previous baseline (and its snapshot) atomically.
    """

    def __init__(self, database: Database) -> None:
        self._db = database

    def save(self, project_root: Path | str, snapshot: Snapshot) -> BaselineRecord:
        normalized = _normalize_root(project_root)
        created_at = _utcnow_iso()
        with self._db.connect() as conn:
            existing = conn.execute(
                "SELECT id FROM baselines WHERE project_root = ?",
                (normalized,),
            ).fetchone()
            if existing is not None:
                # Cascade clears the old snapshot, scans, changes, and alerts.
                conn.execute("DELETE FROM baselines WHERE id = ?", (existing["id"],))
            snapshot_id = _SnapshotWriter.insert(conn, snapshot)
            cursor = conn.execute(
                """
                INSERT INTO baselines(project_root, baseline_snapshot_id, created_at)
                VALUES (?, ?, ?)
                """,
                (normalized, snapshot_id, created_at),
            )
            baseline_id = int(cursor.lastrowid)
        return BaselineRecord(
            baseline_id=baseline_id,
            project_root=normalized,
            created_at=_parse_iso(created_at),
            snapshot=snapshot,
        )

    def find(self, project_root: Path | str) -> BaselineRecord | None:
        normalized = _normalize_root(project_root)
        with self._db.connect() as conn:
            row = conn.execute(
                """
                SELECT id, project_root, baseline_snapshot_id, created_at
                  FROM baselines
                 WHERE project_root = ?
                """,
                (normalized,),
            ).fetchone()
            if row is None:
                return None
            snapshot = _SnapshotWriter.load(conn, int(row["baseline_snapshot_id"]))
        return BaselineRecord(
            baseline_id=int(row["id"]),
            project_root=row["project_root"],
            created_at=_parse_iso(row["created_at"]),
            snapshot=snapshot,
        )


class ScanHistoryRepository:
    """Persist and retrieve scans, their detected changes, and their alerts."""

    def __init__(self, database: Database) -> None:
        self._db = database

    def record_scan(
        self,
        *,
        baseline_id: int,
        project_root: Path | str,
        snapshot: Snapshot,
        changes: Iterable[FileChange],
        alerts: Iterable[Alert],
        started_at: datetime,
        finished_at: datetime | None = None,
    ) -> ScanRecord:
        normalized = _normalize_root(project_root)
        finished = finished_at or datetime.now(timezone.utc)
        change_list = list(changes)
        alert_list = list(alerts)
        with self._db.connect() as conn:
            snapshot_id = _SnapshotWriter.insert(conn, snapshot)
            cursor = conn.execute(
                """
                INSERT INTO scans(
                    baseline_id, snapshot_id, project_root, started_at, finished_at
                ) VALUES (?, ?, ?, ?, ?)
                """,
                (
                    baseline_id,
                    snapshot_id,
                    normalized,
                    started_at.isoformat(),
                    finished.isoformat(),
                ),
            )
            scan_id = int(cursor.lastrowid)
            self._insert_changes(conn, scan_id, change_list)
            self._insert_alerts(conn, scan_id, alert_list)
        critical = sum(1 for a in alert_list if a.severity is Severity.CRITICAL)
        return ScanRecord(
            scan_id=scan_id,
            baseline_id=baseline_id,
            project_root=normalized,
            started_at=started_at,
            finished_at=finished,
            change_count=len(change_list),
            alert_count=len(alert_list),
            critical_count=critical,
        )

    def list_scans(
        self,
        project_root: Path | str,
        *,
        limit: int | None = None,
    ) -> list[ScanRecord]:
        normalized = _normalize_root(project_root)
        sql = """
            SELECT s.id            AS scan_id,
                   s.baseline_id   AS baseline_id,
                   s.project_root  AS project_root,
                   s.started_at    AS started_at,
                   s.finished_at   AS finished_at,
                   (SELECT COUNT(*) FROM changes c WHERE c.scan_id = s.id)
                       AS change_count,
                   (SELECT COUNT(*) FROM alerts  a WHERE a.scan_id = s.id)
                       AS alert_count,
                   (SELECT COUNT(*) FROM alerts  a
                     WHERE a.scan_id = s.id AND a.severity = ?)
                       AS critical_count
              FROM scans s
             WHERE s.project_root = ?
             ORDER BY s.started_at DESC, s.id DESC
        """
        params: tuple = (Severity.CRITICAL.value, normalized)
        if limit is not None:
            sql += " LIMIT ?"
            params = params + (int(limit),)
        with self._db.connect() as conn:
            rows = conn.execute(sql, params).fetchall()
        return [self._row_to_scan(r) for r in rows]

    def latest_scan(self, project_root: Path | str) -> ScanRecord | None:
        results = self.list_scans(project_root, limit=1)
        return results[0] if results else None

    def alerts_for_scan(self, scan_id: int) -> list[Alert]:
        with self._db.connect() as conn:
            rows = conn.execute(
                """
                SELECT relative_path, change_type, severity, rule_name, message
                  FROM alerts
                 WHERE scan_id = ?
                 ORDER BY severity DESC, relative_path ASC
                """,
                (scan_id,),
            ).fetchall()
        return [
            Alert(
                relative_path=r["relative_path"],
                change_type=ChangeType(r["change_type"]),
                severity=Severity(r["severity"]),
                rule_name=r["rule_name"],
                message=r["message"],
            )
            for r in rows
        ]

    @staticmethod
    def _insert_changes(
        conn: sqlite3.Connection,
        scan_id: int,
        changes: list[FileChange],
    ) -> None:
        if not changes:
            return
        conn.executemany(
            """
            INSERT INTO changes(
                scan_id, relative_path, change_type,
                before_sha256, after_sha256, before_size, after_size
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    scan_id,
                    c.relative_path,
                    c.change_type.value,
                    c.before.sha256 if c.before else None,
                    c.after.sha256 if c.after else None,
                    c.before.size_bytes if c.before else None,
                    c.after.size_bytes if c.after else None,
                )
                for c in changes
            ],
        )

    @staticmethod
    def _insert_alerts(
        conn: sqlite3.Connection,
        scan_id: int,
        alerts: list[Alert],
    ) -> None:
        if not alerts:
            return
        conn.executemany(
            """
            INSERT INTO alerts(
                scan_id, relative_path, change_type, severity, rule_name, message
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    scan_id,
                    a.relative_path,
                    a.change_type.value,
                    a.severity.value,
                    a.rule_name,
                    a.message,
                )
                for a in alerts
            ],
        )

    @staticmethod
    def _row_to_scan(row: sqlite3.Row) -> ScanRecord:
        return ScanRecord(
            scan_id=int(row["scan_id"]),
            baseline_id=int(row["baseline_id"]),
            project_root=row["project_root"],
            started_at=_parse_iso(row["started_at"]),
            finished_at=_parse_iso(row["finished_at"]),
            change_count=int(row["change_count"]),
            alert_count=int(row["alert_count"]),
            critical_count=int(row["critical_count"]),
        )
