"""Immutable description of a single tracked file at a point in time."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class FileMetadata:
    """Identity and integrity information for one file in a Snapshot.

    Paths are stored as POSIX-style relative paths (relative to the monitored
    project root) so snapshots are portable across machines and OSes.
    """

    relative_path: str
    size_bytes: int
    modified_at: float  # POSIX timestamp (seconds since epoch)
    sha256: str

    def __post_init__(self) -> None:
        if not self.relative_path:
            raise ValueError("relative_path must not be empty")
        if self.size_bytes < 0:
            raise ValueError("size_bytes must be non-negative")
        if len(self.sha256) != 64:
            raise ValueError("sha256 must be a 64-character hex digest")
        try:
            int(self.sha256, 16)
        except ValueError as exc:
            raise ValueError("sha256 must be a hex digest") from exc
