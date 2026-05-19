"""CodeGuard entry point.

Stage 1: minimal launcher. The GUI is wired in a later stage.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Make `src/` importable without requiring `pip install -e .`.
# Keeps the project zero-config for the college environment.
_SRC = Path(__file__).resolve().parent / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from codeguard import __version__


def main() -> int:
    print(f"CodeGuard v{__version__} — starting…")
    print("(GUI not wired yet — coming in a later stage.)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
