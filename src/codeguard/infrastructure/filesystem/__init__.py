"""Filesystem adapters: scanning, hashing, ignore-pattern matching."""

from .scanner import FileScanner, ScanResult

__all__ = ["FileScanner", "ScanResult"]
