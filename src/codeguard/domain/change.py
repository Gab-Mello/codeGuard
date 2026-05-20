"""Detected differences between two snapshots."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from .file_metadata import FileMetadata


class ChangeType(str, Enum):
    CREATED = "CREATED"
    MODIFIED = "MODIFIED"
    DELETED = "DELETED"


@dataclass(frozen=True, slots=True)
class FileChange:
    """A single detected change between two snapshots.

    `before` is None for CREATED; `after` is None for DELETED. For MODIFIED,
    both are present and at least one of size/hash differs.
    """

    relative_path: str
    change_type: ChangeType
    before: FileMetadata | None
    after: FileMetadata | None

    def __post_init__(self) -> None:
        if self.change_type is ChangeType.CREATED:
            if self.before is not None or self.after is None:
                raise ValueError("CREATED requires after only")
        elif self.change_type is ChangeType.DELETED:
            if self.before is None or self.after is not None:
                raise ValueError("DELETED requires before only")
        elif self.change_type is ChangeType.MODIFIED:
            if self.before is None or self.after is None:
                raise ValueError("MODIFIED requires both before and after")
