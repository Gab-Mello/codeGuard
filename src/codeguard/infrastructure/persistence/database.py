"""SQLite connection management and schema initialization."""

from __future__ import annotations

import logging
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator


_logger = logging.getLogger(__name__)


_SCHEMA_VERSION = 1


class SchemaVersionMismatchError(RuntimeError):
    """Raised when an existing database was written by a different schema version."""

    def __init__(self, found: int, expected: int) -> None:
        super().__init__(
            f"database schema version {found} is incompatible with "
            f"this CodeGuard build (expected {expected})"
        )
        self.found = found
        self.expected = expected


_SCHEMA_STATEMENTS: tuple[str, ...] = (
    """
    CREATE TABLE IF NOT EXISTS snapshots (
        id           INTEGER PRIMARY KEY AUTOINCREMENT,
        project_root TEXT    NOT NULL,
        created_at   TEXT    NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS file_metadata (
        id            INTEGER PRIMARY KEY AUTOINCREMENT,
        snapshot_id   INTEGER NOT NULL REFERENCES snapshots(id) ON DELETE CASCADE,
        relative_path TEXT    NOT NULL,
        size_bytes    INTEGER NOT NULL,
        modified_at   REAL    NOT NULL,
        sha256        TEXT    NOT NULL,
        UNIQUE(snapshot_id, relative_path)
    )
    """,
    """
    CREATE INDEX IF NOT EXISTS ix_file_metadata_snapshot
        ON file_metadata(snapshot_id)
    """,
    """
    CREATE INDEX IF NOT EXISTS ix_file_metadata_relative_path
        ON file_metadata(relative_path)
    """,
    """
    CREATE TABLE IF NOT EXISTS baselines (
        id                   INTEGER PRIMARY KEY AUTOINCREMENT,
        baseline_snapshot_id INTEGER NOT NULL REFERENCES snapshots(id) ON DELETE CASCADE,
        created_at           TEXT    NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS scans (
        id           INTEGER PRIMARY KEY AUTOINCREMENT,
        baseline_id  INTEGER NOT NULL REFERENCES baselines(id) ON DELETE CASCADE,
        snapshot_id  INTEGER NOT NULL REFERENCES snapshots(id) ON DELETE CASCADE,
        started_at   TEXT    NOT NULL,
        finished_at  TEXT    NOT NULL
    )
    """,
    """
    CREATE INDEX IF NOT EXISTS ix_scans_baseline_started
        ON scans(baseline_id, started_at DESC)
    """,
    """
    CREATE TABLE IF NOT EXISTS changes (
        id            INTEGER PRIMARY KEY AUTOINCREMENT,
        scan_id       INTEGER NOT NULL REFERENCES scans(id) ON DELETE CASCADE,
        relative_path TEXT    NOT NULL,
        change_type   TEXT    NOT NULL,
        before_sha256 TEXT,
        after_sha256  TEXT,
        before_size   INTEGER,
        after_size    INTEGER
    )
    """,
    """
    CREATE INDEX IF NOT EXISTS ix_changes_scan
        ON changes(scan_id)
    """,
    """
    CREATE TABLE IF NOT EXISTS alerts (
        id            INTEGER PRIMARY KEY AUTOINCREMENT,
        scan_id       INTEGER NOT NULL REFERENCES scans(id) ON DELETE CASCADE,
        relative_path TEXT    NOT NULL,
        change_type   TEXT    NOT NULL,
        severity      TEXT    NOT NULL,
        rule_name     TEXT    NOT NULL,
        message       TEXT    NOT NULL
    )
    """,
    """
    CREATE INDEX IF NOT EXISTS ix_alerts_scan_severity
        ON alerts(scan_id, severity)
    """,
)


class Database:
    """Owns the SQLite database file and hands out connections.

    Creates the parent directory and initializes the schema on first use.
    Connections are configured with `Row` row factory and foreign-key
    enforcement enabled so repositories can rely on referential integrity.

    Initialization is lazy and not thread-safe: callers are assumed to be
    single-threaded.
    """

    def __init__(self, path: Path | str) -> None:
        self._path = Path(path)
        self._initialized = False

    @property
    def path(self) -> Path:
        return self._path

    def initialize(self) -> None:
        """Create the database file (and parent directories) and apply schema.

        Stamps `PRAGMA user_version` with `_SCHEMA_VERSION` on a fresh database
        and refuses to open one written by an incompatible build.
        """
        self._path.parent.mkdir(parents=True, exist_ok=True)
        conn = self._raw_connect()
        try:
            with conn:
                found = conn.execute("PRAGMA user_version").fetchone()[0]
                if found == 0:
                    for statement in _SCHEMA_STATEMENTS:
                        conn.execute(statement)
                    conn.execute(f"PRAGMA user_version = {_SCHEMA_VERSION}")
                elif found != _SCHEMA_VERSION:
                    raise SchemaVersionMismatchError(found, _SCHEMA_VERSION)
                else:
                    for statement in _SCHEMA_STATEMENTS:
                        conn.execute(statement)
        finally:
            conn.close()
        self._initialized = True
        _logger.info("database initialised at %s", self._path)

    @contextmanager
    def connect(self) -> Iterator[sqlite3.Connection]:
        """Yield a configured connection inside a transaction."""
        if not self._initialized:
            self.initialize()
        conn = self._raw_connect()
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def _raw_connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(
            self._path,
            detect_types=sqlite3.PARSE_DECLTYPES,
            isolation_level="DEFERRED",
        )
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        return conn
