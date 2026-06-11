"""Path filtering rules used to exclude files and directories from scans.

Patterns are matched against POSIX-style relative paths in two flavors:

  * Patterns containing a "/" match the full relative path via fnmatch
    (e.g. "build/*", "src/**/*.bak").
  * Patterns without a "/" match any path *segment* by name
    (e.g. ".git" matches ".git", "pkg/.git", "pkg/.git/HEAD";
    "*.pyc" matches any segment ending in .pyc).

This is intentionally simpler than full gitignore semantics, enough for
the common cases (`.git`, `__pycache__`, `node_modules`, `*.pyc`, ...)
without dragging in a parser.
"""

from __future__ import annotations

import fnmatch


IGNORE_PATTERNS: tuple[str, ...] = (
    ".git",
    ".codeguard",
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

_SEGMENT_PATTERNS: tuple[str, ...] = tuple(p for p in IGNORE_PATTERNS if "/" not in p)
_PATH_PATTERNS: tuple[str, ...] = tuple(p for p in IGNORE_PATTERNS if "/" in p)


def should_ignore(relative_posix_path: str) -> bool:
    """Return True if `relative_posix_path` matches any ignore pattern."""
    if not relative_posix_path:
        return False
    for full_pat in _PATH_PATTERNS:
        if fnmatch.fnmatchcase(relative_posix_path, full_pat):
            return True
    for segment in relative_posix_path.split("/"):
        for seg_pat in _SEGMENT_PATTERNS:
            if fnmatch.fnmatchcase(segment, seg_pat):
                return True
    return False
