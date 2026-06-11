"""Filesystem adapters: scanning, hashing, ignore-pattern matching."""

from .ignore import IgnoreMatcher
from .scanner import FileScanner, ScanResult

__all__ = ["FileScanner", "IgnoreMatcher", "ScanResult"]
