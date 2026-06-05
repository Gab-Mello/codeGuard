"""Filesystem adapters: scanning, hashing, ignore-pattern matching."""

from .hashing import FileHasher
from .ignore import IgnoreMatcher

__all__ = ["FileHasher", "IgnoreMatcher"]
