"""
Data models for Project Cleaner.
"""

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import List, Optional


def format_size(bytes_num: int) -> str:
    """Format bytes into human readable format (KB, MB, GB)."""
    if bytes_num < 0:
        return "0 B"
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if bytes_num < 1024.0:
            return f"{bytes_num:.1f} {unit}" if unit != "B" else f"{bytes_num} B"
        bytes_num /= 1024.0
    return f"{bytes_num:.1f} PB"


def format_relative_time(dt: datetime) -> str:
    """Format a datetime into relative human time (e.g. '3 days ago')."""
    now = datetime.now()
    diff = now - dt

    seconds = diff.total_seconds()
    if seconds < 0:
        return "just now"
    if seconds < 60:
        return f"{int(seconds)}s ago"
    minutes = seconds / 60
    if minutes < 60:
        return f"{int(minutes)}m ago"
    hours = minutes / 60
    if hours < 24:
        return f"{int(hours)}h ago"
    days = hours / 24
    if days < 30:
        return f"{int(days)}d ago"
    months = days / 30
    if months < 12:
        return f"{int(months)}mo ago"
    years = days / 365
    return f"{int(years)}y ago"


@dataclass
class CleanTarget:
    """Represents a specific directory or file that can be cleaned."""
    path: Path
    project_path: Path
    size_bytes: int = 0
    is_dir: bool = True
    target_type: str = ""  # e.g., 'node_modules', 'build', '.dart_tool'
    is_optional: bool = False  # e.g., virtualenv

    @property
    def relative_to_project(self) -> str:
        try:
            return str(self.path.relative_to(self.project_path))
        except ValueError:
            return self.path.name

    @property
    def relative_path(self) -> str:
        return self.relative_to_project

    @property
    def formatted_size(self) -> str:
        return format_size(self.size_bytes)


@dataclass
class Project:
    """Represents a detected software project."""
    path: Path
    name: str
    project_type: str  # 'flutter', 'node', 'python', 'gradle', etc.
    display_name: str
    targets: List[CleanTarget] = field(default_factory=list)
    last_modified: Optional[datetime] = None
    has_clean_command: bool = False

    @property
    def total_cleanable_bytes(self) -> int:
        return sum(t.size_bytes for t in self.targets)

    @property
    def formatted_total_size(self) -> str:
        return format_size(self.total_cleanable_bytes)

    @property
    def formatted_last_modified(self) -> str:
        if self.last_modified:
            return format_relative_time(self.last_modified)
        return "Unknown"

    @property
    def days_since_modified(self) -> int:
        if not self.last_modified:
            return 9999
        return (datetime.now() - self.last_modified).days


@dataclass
class DeletedEntry:
    """Detailed record of a deleted item for logging."""
    path: Path
    relative_path: str
    size_bytes: int
    mode: str = "permanent"  # 'permanent', 'trash', 'command'
    project_name: str = ""
    timestamp: datetime = field(default_factory=datetime.now)

    @property
    def formatted_size(self) -> str:
        return format_size(self.size_bytes)


@dataclass
class CleanResult:
    """Summary of cleaning execution."""
    freed_bytes: int = 0
    deleted_items: List[str] = field(default_factory=list)
    deleted_entries: List[DeletedEntry] = field(default_factory=list)
    failed_items: List[tuple[str, str]] = field(default_factory=list)  # (item, error)
    commands_executed: List[str] = field(default_factory=list)
    skipped_items: List[str] = field(default_factory=list)

    @property
    def formatted_freed(self) -> str:
        return format_size(self.freed_bytes)
