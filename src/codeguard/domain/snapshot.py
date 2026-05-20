"""Trusted state of a monitored project at a point in time."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone

from .file_metadata import FileMetadata


@dataclass(slots=True)
class Snapshot:
    """A collection of FileMetadata describing a project at one point in time."""

    project_root: str
    files: dict[str, FileMetadata] = field(default_factory=dict)
    created_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    snapshot_id: int | None = None  # assigned by the repository on persist

    def add(self, metadata: FileMetadata) -> None:
        self.files[metadata.relative_path] = metadata

    def __len__(self) -> int:
        return len(self.files)

    def __contains__(self, relative_path: object) -> bool:
        return relative_path in self.files

    def get(self, relative_path: str) -> FileMetadata | None:
        return self.files.get(relative_path)

    def paths(self) -> set[str]:
        return set(self.files.keys())
