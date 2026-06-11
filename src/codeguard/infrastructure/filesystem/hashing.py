"""Streamed SHA-256 hashing for files of arbitrary size."""

from __future__ import annotations

import hashlib
from pathlib import Path


DEFAULT_CHUNK_SIZE = 64 * 1024


def hash_file(path: Path | str, *, chunk_size: int = DEFAULT_CHUNK_SIZE) -> str:
    """Return the lowercase 64-character hex SHA-256 digest of `path`.

    Reads the file in fixed-size chunks so memory usage stays constant
    regardless of file size.
    """
    digest = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(chunk_size), b""):
            digest.update(chunk)
    return digest.hexdigest()
