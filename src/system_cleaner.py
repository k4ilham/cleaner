"""
System and Developer Global Cache Scanner & Cleaner.
Handles:
- ~/.gradle/caches (Gradle build caches)
- ~/.npm (NPM cache)
- ~/Library/Developer/Xcode/DerivedData (Xcode DerivedData)
- ~/Library/Developer/CoreSimulator/Caches & Devices (iOS Simulators)
- ~/Library/Caches (Chrome, Telegram, Playwright, Pip, etc.)
- Homebrew cache
"""

import os
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

from .models import CleanResult, DeletedEntry, format_size
from .trash import delete_target
from .utils import get_path_size


@dataclass
class SystemCacheItem:
    key: str
    name: str
    category: str  # "Developer Tools", "App Caches", "System / AI"
    path: Path
    description: str
    size_bytes: int = 0
    safe_to_delete: bool = True
    clean_command: Optional[List[str]] = None

    @property
    def formatted_size(self) -> str:
        return format_size(self.size_bytes)


def get_known_system_caches() -> List[SystemCacheItem]:
    """Return list of known heavy developer and system caches on macOS."""
    home = Path.home()

    return [
        SystemCacheItem(
            key="gradle_cache",
            name="Gradle Global Cache",
            category="Developer Tools",
            path=home / ".gradle" / "caches",
            description="Cache dependensi library Android & Java (~/.gradle/caches).",
        ),
        SystemCacheItem(
            key="npm_cache",
            name="NPM Global Cache",
            category="Developer Tools",
            path=home / ".npm",
            description="Cache paket node_modules global dari npm (~/.npm).",
            clean_command=["npm", "cache", "clean", "--force"],
        ),
        SystemCacheItem(
            key="gemini_backup",
            name="Antigravity / Gemini Backup",
            category="AI / Agent Backups",
            path=home / ".gemini" / "antigravity-backup",
            description="Cadangan file sesi lama Antigravity/Gemini yang tidak lagi digunakan.",
        ),
        SystemCacheItem(
            key="chrome_cache",
            name="Google Chrome Cache",
            category="Browser Caches",
            path=home / "Library" / "Caches" / "Google" / "Chrome",
            description="Cache browsing, gambar web, dan data sementara Google Chrome.",
        ),
        SystemCacheItem(
            key="xcode_derived",
            name="Xcode DerivedData",
            category="Developer Tools",
            path=home / "Library" / "Developer" / "Xcode" / "DerivedData",
            description="File kompilasi sementara dan indeks build Xcode/iOS.",
        ),
        SystemCacheItem(
            key="xcode_simulators",
            name="Xcode Simulator Caches",
            category="Developer Tools",
            path=home / "Library" / "Developer" / "CoreSimulator" / "Caches",
            description="File cache runtime simulator iPhone/iPad.",
        ),
        SystemCacheItem(
            key="playwright_cache",
            name="Playwright Browsers Cache",
            category="Developer Tools",
            path=home / "Library" / "Caches" / "ms-playwright",
            description="Binary browser headless (Chromium/Firefox/WebKit) dari Playwright.",
        ),
        SystemCacheItem(
            key="telegram_cache",
            name="Telegram Media Cache",
            category="App Caches",
            path=home / "Library" / "Caches" / "ru.keepcoder.Telegram",
            description="Cache video, foto, dan file kiriman di aplikasi Telegram Desktop.",
        ),
        SystemCacheItem(
            key="github_shipit",
            name="GitHub Desktop Cache",
            category="App Caches",
            path=home / "Library" / "Caches" / "com.github.GitHubClient.ShipIt",
            description="Cache installer updater GitHub Desktop.",
        ),
        SystemCacheItem(
            key="trae_cache",
            name="Trae Editor Cache",
            category="App Caches",
            path=home / "Library" / "Caches" / "Trae",
            description="Cache editor Trae.",
        ),
        SystemCacheItem(
            key="pip_cache",
            name="Pip Cache",
            category="Developer Tools",
            path=home / "Library" / "Caches" / "pip",
            description="Cache wheel dan tar.gz paket Python yang telah diunduh.",
            clean_command=["python3", "-m", "pip", "cache", "purge"],
        ),
        SystemCacheItem(
            key="homebrew_cache",
            name="Homebrew Cache",
            category="System",
            path=home / "Library" / "Caches" / "Homebrew",
            description="Cache tarball dan installer Homebrew.",
            clean_command=["brew", "cleanup", "--prune=all"],
        ),
    ]


def scan_system_caches() -> List[SystemCacheItem]:
    """Scan and compute sizes for all existing system caches."""
    items = get_known_system_caches()
    active_items: List[SystemCacheItem] = []

    for item in items:
        if item.path.exists():
            item.size_bytes = get_path_size(item.path)
            if item.size_bytes > 50 * 1024 * 1024:  # Only report if > 50 MB
                active_items.append(item)

    active_items.sort(key=lambda x: x.size_bytes, reverse=True)
    return active_items


def clean_system_cache_item(
    item: SystemCacheItem,
    dry_run: bool = False,
    use_trash: bool = False,
) -> CleanResult:
    """Clean a specific system cache item."""
    result = CleanResult()
    deletion_mode = "trash" if use_trash else "permanent"

    if not item.path.exists():
        result.skipped_items.append(str(item.path))
        return result

    if dry_run:
        result.freed_bytes += item.size_bytes
        result.deleted_items.append(f"[DRY-RUN] {item.name}")
        return result

    # If item has a specific CLI tool clean command (e.g. npm cache clean or pip cache purge)
    if item.clean_command and shutil.which(item.clean_command[0]):
        try:
            cmd_proc = subprocess.run(
                item.clean_command,
                capture_output=True,
                text=True,
                timeout=30,
                check=False,
            )
            if cmd_proc.returncode == 0:
                result.commands_executed.append(" ".join(item.clean_command))
        except Exception:
            pass

    # If path still exists, remove contents or folder
    if item.path.exists():
        # For cache directories, deleting contents or folder
        success, error = delete_target(item.path, use_trash=use_trash)
        if success:
            result.freed_bytes += item.size_bytes
            result.deleted_items.append(item.name)
            result.deleted_entries.append(
                DeletedEntry(
                    path=item.path,
                    relative_path=item.name,
                    size_bytes=item.size_bytes,
                    mode=deletion_mode,
                    project_name=f"[SYSTEM] {item.name}",
                )
            )
        else:
            result.failed_items.append((item.name, error))
    else:
        # Was already cleaned by command
        result.freed_bytes += item.size_bytes
        result.deleted_items.append(f"{item.name} (via command)")
        result.deleted_entries.append(
            DeletedEntry(
                path=item.path,
                relative_path=item.name,
                size_bytes=item.size_bytes,
                mode="command",
                project_name=f"[SYSTEM] {item.name}",
            )
        )

    return result
