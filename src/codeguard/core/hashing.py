"""SHA-256 file hashing — streamed so large files don't load into memory."""

from __future__ import annotations

import hashlib
from pathlib import Path


class FileHasher:
    """Computes SHA-256 hex digests of files using chunked reads.

    The chunk size is configurable but defaults to 64 KiB, which is a good
    trade-off between syscall overhead and memory footprint for typical
    project files. I/O errors (missing file, permission denied, etc.) are
    not caught here — the caller decides policy.
    """

    DEFAULT_CHUNK_SIZE = 64 * 1024

    def __init__(self, chunk_size: int = DEFAULT_CHUNK_SIZE) -> None:
        if chunk_size <= 0:
            raise ValueError("chunk_size must be positive")
        self._chunk_size = chunk_size

    @property
    def chunk_size(self) -> int:
        return self._chunk_size

    def hash_file(self, path: Path | str) -> str:
        """Return the lowercase 64-character hex SHA-256 digest of `path`."""
        digest = hashlib.sha256()
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(self._chunk_size), b""):
                digest.update(chunk)
        return digest.hexdigest()
