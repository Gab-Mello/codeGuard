"""IgnoreMatcher — gitignore-flavored path filtering for the scanner.

Patterns are matched against POSIX-style relative paths. Two flavors:

  * Patterns containing a "/" match the full relative path via fnmatch
    (e.g. "build/*", "src/**/*.bak").
  * Patterns without a "/" match any path *segment* by name
    (e.g. ".git" matches ".git", "pkg/.git", "pkg/.git/HEAD";
    "*.pyc" matches any segment ending in .pyc).

This is intentionally simpler than full gitignore semantics — enough for
the requirements (`.git`, `__pycache__`, `node_modules`, `*.pyc`, ...)
without dragging in a parser.
"""

from __future__ import annotations

import fnmatch
from collections.abc import Iterable


class IgnoreMatcher:
    DEFAULT_PATTERNS: tuple[str, ...] = (
        ".git",
        "__pycache__",
        ".venv",
        "venv",
        "node_modules",
        "dist",
        "build",
        ".idea",
        ".vscode",
        ".DS_Store",
        "*.pyc",
        "*.log",
    )

    def __init__(self, patterns: Iterable[str] | None = None) -> None:
        chosen = self.DEFAULT_PATTERNS if patterns is None else tuple(patterns)
        self._segment_patterns: tuple[str, ...] = tuple(
            p for p in chosen if "/" not in p
        )
        self._path_patterns: tuple[str, ...] = tuple(
            p for p in chosen if "/" in p
        )

    @property
    def patterns(self) -> tuple[str, ...]:
        return self._segment_patterns + self._path_patterns

    def matches(self, relative_posix_path: str) -> bool:
        """Return True if the path should be ignored."""
        if not relative_posix_path:
            return False
        for full_pat in self._path_patterns:
            if fnmatch.fnmatchcase(relative_posix_path, full_pat):
                return True
        if self._segment_patterns:
            for segment in relative_posix_path.split("/"):
                for seg_pat in self._segment_patterns:
                    if fnmatch.fnmatchcase(segment, seg_pat):
                        return True
        return False
