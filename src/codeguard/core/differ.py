"""Comparison of snapshots into a list of detected file changes."""

from __future__ import annotations

from ..domain import ChangeType, FileChange, Snapshot


class SnapshotDiffer:
    """Computes the set of file changes between two snapshots.

    A file is MODIFIED only when its SHA-256 differs — size or mtime alone
    are not sufficient signals because mtime can be touched without content
    actually changing.
    """

    def diff(self, baseline: Snapshot, current: Snapshot) -> list[FileChange]:
        """Return the changes that turn `baseline` into `current`.

        The result is sorted by relative path so the output is deterministic
        and easy to render in a table.
        """
        changes: list[FileChange] = []
        baseline_paths = baseline.paths()
        current_paths = current.paths()

        for path in current_paths - baseline_paths:
            after = current.get(path)
            assert after is not None  # path came from current.paths()
            changes.append(
                FileChange(
                    relative_path=path,
                    change_type=ChangeType.CREATED,
                    before=None,
                    after=after,
                )
            )

        for path in baseline_paths - current_paths:
            before = baseline.get(path)
            assert before is not None
            changes.append(
                FileChange(
                    relative_path=path,
                    change_type=ChangeType.DELETED,
                    before=before,
                    after=None,
                )
            )

        for path in baseline_paths & current_paths:
            before = baseline.get(path)
            after = current.get(path)
            assert before is not None and after is not None
            if before.sha256 != after.sha256:
                changes.append(
                    FileChange(
                        relative_path=path,
                        change_type=ChangeType.MODIFIED,
                        before=before,
                        after=after,
                    )
                )

        changes.sort(key=lambda c: c.relative_path)
        return changes
