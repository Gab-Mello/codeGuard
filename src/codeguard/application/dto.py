"""Application-layer data transfer objects returned by use cases.

These describe the *shape* of persisted records the application orchestrates;
infrastructure adapters construct and return them, but the types themselves
belong to the application layer so it never has to import infrastructure to
talk about its own results.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from ..domain import Snapshot


@dataclass(slots=True)
class BaselineRecord:
    """Stored baseline plus its captured snapshot."""

    baseline_id: int
    created_at: datetime
    snapshot: Snapshot


@dataclass(slots=True)
class ScanRecord:
    """Summary row for one persisted scan."""

    scan_id: int
    baseline_id: int
    started_at: datetime
    finished_at: datetime
    change_count: int
    alert_count: int
    critical_count: int
