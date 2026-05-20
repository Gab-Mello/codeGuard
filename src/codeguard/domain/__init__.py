"""Domain layer — pure data classes and value objects (no I/O)."""

from .alert import Alert, Severity
from .change import ChangeType, FileChange
from .file_metadata import FileMetadata
from .snapshot import Snapshot

__all__ = [
    "Alert",
    "ChangeType",
    "FileChange",
    "FileMetadata",
    "Severity",
    "Snapshot",
]
