"""FileScanner — walks a folder, skips ignored entries, builds a Snapshot."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from ..domain import FileMetadata, Snapshot
from .hashing import FileHasher
from .ignore import IgnoreMatcher


@dataclass(slots=True)
class ScanResult:
    """Outcome of a scan: the snapshot plus any files we couldn't read."""

    snapshot: Snapshot
    skipped: list[tuple[str, str]] = field(default_factory=list)
    """Pairs of (relative_posix_path, reason) for files that were skipped."""


class FileScanner:
    """Walks a project folder and produces a Snapshot.

    Associations:
      * uses an `IgnoreMatcher` to prune unwanted paths
      * uses a `FileHasher` to compute SHA-256 digests

    Both are constructor-injected so tests and future stages can swap
    behavior (e.g. a stricter ignore set, a faster mock hasher).
    """

    def __init__(
        self,
        hasher: FileHasher | None = None,
        ignore_matcher: IgnoreMatcher | None = None,
    ) -> None:
        self._hasher = hasher or FileHasher()
        self._ignore = ignore_matcher or IgnoreMatcher()

    @property
    def hasher(self) -> FileHasher:
        return self._hasher

    @property
    def ignore_matcher(self) -> IgnoreMatcher:
        return self._ignore

    def scan(self, project_root: Path | str) -> ScanResult:
        """Scan `project_root` and return the resulting snapshot + skipped list.

        Symlinks are not followed. Directories matching the ignore matcher
        are pruned in-place so we never descend into them. Per-file I/O
        errors (permission denied, vanished mid-scan) are recorded in
        `ScanResult.skipped` instead of crashing the scan.
        """
        root = Path(project_root).resolve()
        if not root.exists():
            raise FileNotFoundError(f"project root does not exist: {root}")
        if not root.is_dir():
            raise NotADirectoryError(f"project root is not a directory: {root}")

        snapshot = Snapshot(project_root=str(root))
        skipped: list[tuple[str, str]] = []

        for dirpath, dirnames, filenames in os.walk(root, followlinks=False):
            current = Path(dirpath)
            rel_dir = self._relative_posix(current, root)

            # Prune ignored directories in-place so os.walk never descends.
            dirnames[:] = [
                d for d in dirnames
                if not self._ignore.matches(self._join_rel(rel_dir, d))
            ]

            for name in filenames:
                rel_file = self._join_rel(rel_dir, name)
                if self._ignore.matches(rel_file):
                    continue
                file_path = current / name
                try:
                    if file_path.is_symlink() or not file_path.is_file():
                        continue
                    stat = file_path.stat()
                    digest = self._hasher.hash_file(file_path)
                except OSError as exc:
                    skipped.append((rel_file, f"{type(exc).__name__}: {exc}"))
                    continue
                snapshot.add(
                    FileMetadata(
                        relative_path=rel_file,
                        size_bytes=stat.st_size,
                        modified_at=stat.st_mtime,
                        sha256=digest,
                    )
                )

        return ScanResult(snapshot=snapshot, skipped=skipped)

    @staticmethod
    def _relative_posix(path: Path, root: Path) -> str:
        rel = path.relative_to(root)
        # POSIX-style, "" for the root itself
        s = rel.as_posix()
        return "" if s == "." else s

    @staticmethod
    def _join_rel(rel_dir: str, name: str) -> str:
        return name if not rel_dir else f"{rel_dir}/{name}"
