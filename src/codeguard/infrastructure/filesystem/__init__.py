"""Filesystem adapters: scanning, hashing, ignore-pattern matching."""

from .hashing import FileHasher
from .ignore import IgnoreMatcher
from .scanner import FileScanner, ScanResult

__all__ = ["FileHasher", "FileScanner", "IgnoreMatcher", "ScanResult"]
