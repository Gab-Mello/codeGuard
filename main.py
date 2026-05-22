"""CodeGuard application entry point."""

from __future__ import annotations

import sys
from pathlib import Path

# Make `src/` importable without requiring `pip install -e .`.
# Keeps the project zero-config for the college environment.
_SRC = Path(__file__).resolve().parent / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from codeguard.cli.app import app


if __name__ == "__main__":
    app()
