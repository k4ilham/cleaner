"""
Utility functions for file inspection, sizing, and date checking.
"""

import os
from datetime import datetime
from pathlib import Path
from typing import Optional


def _get_entry_size(stat_res) -> int:
    """Calculate actual physical disk space, accounting for sparse files."""
    if hasattr(stat_res, "st_blocks") and stat_res.st_blocks > 0:
        physical = stat_res.st_blocks * 512
        return min(stat_res.st_size, physical)
    return stat_res.st_size


def get_path_size(path: Path) -> int:
    """
    Calculate the total size of a file or directory in bytes.
    Ignores symlinks to prevent infinite recursion and duplicate counting.
    Accurately handles sparse files on macOS APFS.
    """
    if not path.exists():
        return 0

    if path.is_symlink():
        return 0

    if path.is_file():
        try:
            return _get_entry_size(path.stat())
        except (OSError, PermissionError):
            return 0

    total_size = 0
    stack = [str(path)]

    while stack:
        current_dir = stack.pop()
        try:
            with os.scandir(current_dir) as entries:
                for entry in entries:
                    try:
                        if entry.is_symlink():
                            continue
                        if entry.is_file():
                            total_size += _get_entry_size(entry.stat())
                        elif entry.is_dir():
                            stack.append(entry.path)
                    except (OSError, PermissionError):
                        continue
        except (OSError, PermissionError):
            continue

    return total_size


def get_last_modified(path: Path, max_depth: int = 2) -> Optional[datetime]:
    """
    Get the most recent modification time of files in a directory (up to max_depth).
    Falls back to directory stat if no files scanned.
    """
    latest_mtime = 0.0

    try:
        latest_mtime = max(latest_mtime, path.stat().st_mtime)
    except (OSError, PermissionError):
        pass

    def _scan(current_path: Path, current_depth: int):
        nonlocal latest_mtime
        if current_depth > max_depth:
            return
        try:
            with os.scandir(current_path) as entries:
                for entry in entries:
                    try:
                        if entry.is_symlink() or entry.name in {".git", "node_modules", "build", ".dart_tool"}:
                            continue
                        mtime = entry.stat().st_mtime
                        if mtime > latest_mtime:
                            latest_mtime = mtime
                        if entry.is_dir():
                            _scan(Path(entry.path), current_depth + 1)
                    except (OSError, PermissionError):
                        continue
        except (OSError, PermissionError):
            pass

    _scan(path, 1)

    if latest_mtime > 0:
        return datetime.fromtimestamp(latest_mtime)
    return None
