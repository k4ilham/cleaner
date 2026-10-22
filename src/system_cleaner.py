"""
System and Developer Global Cache Scanner & Cleaner.
Supports Windows, macOS, and Linux.
Handles:
- Windows User Temp (%TEMP%) & System Temp
- Windows Update Download Cache (SoftwareDistribution/Download)
- Crash Dumps & Windows Error Reporting (WER)
- Windows Recycle Bins (C: & D:)
- Chrome, Edge, and browser caches
- Developer caches: Gradle, NPM, Pip, Composer, NuGet, Go, Cargo, VS Code
- macOS caches: ~/Library/Caches, Xcode DerivedData, Simulators, Homebrew
"""

import os
import platform
import shutil
import subprocess
import sys
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
    category: str  # "System Caches", "Developer Tools", "Browser Caches", "AI / Agent Backups"
    path: Path
    description: str
    size_bytes: int = 0
    safe_to_delete: bool = True
    clean_command: Optional[List[str]] = None
    clean_contents_only: bool = False  # If True, delete contents inside instead of removing directory itself

    @property
    def formatted_size(self) -> str:
        return format_size(self.size_bytes)


def _get_windows_recycle_bin_info(drive_letter: str) -> tuple[int, int]:
    """Query size and items count for a specific Windows drive recycle bin."""
    try:
        import ctypes
        from ctypes import wintypes

        class SHQUERYRBINFO(ctypes.Structure):
            _fields_ = [
                ("cbSize", wintypes.DWORD),
                ("i64Size", ctypes.c_int64),
                ("i64NumItems", ctypes.c_int64),
            ]

        rbinfo = SHQUERYRBINFO()
        rbinfo.cbSize = ctypes.sizeof(SHQUERYRBINFO)
        ret = ctypes.windll.shell32.SHQueryRecycleBinW(f"{drive_letter}:\\", ctypes.byref(rbinfo))
        if ret == 0:
            return int(rbinfo.i64Size), int(rbinfo.i64NumItems)
    except Exception:
        pass
    return 0, 0


def _empty_windows_recycle_bin(drive_letter: Optional[str] = None) -> bool:
    """Empty Windows Recycle Bin via native Win32 API without UI prompts."""
    try:
        import ctypes

        root = f"{drive_letter}:\\" if drive_letter else None
        # SHERB_NOCONFIRMATION (0x1) | SHERB_NOPROGRESSUI (0x2) | SHERB_NOSOUND (0x4) = 7
        flags = 7
        ret = ctypes.windll.shell32.SHEmptyRecycleBinW(None, root, flags)
        return ret == 0
    except Exception:
        return False


def get_windows_system_caches() -> List[SystemCacheItem]:
    """Return list of known heavy developer, browser, and system caches on Windows."""
    home = Path.home()
    local_app_data_str = os.environ.get("LOCALAPPDATA")
    app_data_str = os.environ.get("APPDATA")
    temp_str = os.environ.get("TEMP")

    local_app_data = Path(local_app_data_str) if local_app_data_str else home / "AppData" / "Local"
    app_data = Path(app_data_str) if app_data_str else home / "AppData" / "Roaming"
    temp_dir = Path(temp_str) if temp_str else local_app_data / "Temp"

    items: List[SystemCacheItem] = []

    # 1. Windows System & Temp Caches
    items.extend([
        SystemCacheItem(
            key="win_user_temp",
            name="Windows User Temp (%TEMP%)",
            category="System Caches",
            path=temp_dir,
            description="Berkas sementara aplikasi & sistem (%TEMP%).",
            clean_contents_only=True,
        ),
        SystemCacheItem(
            key="win_sys_temp",
            name="Windows System Temp",
            category="System Caches",
            path=Path("C:/Windows/Temp"),
            description="Berkas sementara sistem Windows di C:\\Windows\\Temp.",
            clean_contents_only=True,
        ),
        SystemCacheItem(
            key="win_update_download",
            name="Windows Update Download Cache",
            category="System Caches",
            path=Path("C:/Windows/SoftwareDistribution/Download"),
            description="Installer sisa update Windows yang sudah selesai diunduh.",
            clean_contents_only=True,
        ),
        SystemCacheItem(
            key="win_crash_dumps",
            name="Windows Crash Dumps (.dmp)",
            category="System Caches",
            path=local_app_data / "CrashDumps",
            description="Dump memori program saat error / crash di AppData\\Local\\CrashDumps.",
            clean_contents_only=True,
        ),
        SystemCacheItem(
            key="win_wer",
            name="Windows Error Reporting",
            category="System Caches",
            path=local_app_data / "Microsoft" / "Windows" / "WER",
            description="Antrean laporan crash Windows Error Reporting.",
            clean_contents_only=True,
        ),
    ])

    # 2. Recycle Bins for available drives (C:, D:, etc.)
    for drive in ["C", "D"]:
        drive_path = Path(f"{drive}:/")
        if drive_path.exists():
            items.append(
                SystemCacheItem(
                    key=f"recycle_bin_{drive.lower()}",
                    name=f"Recycle Bin Drive {drive}:",
                    category="System Caches",
                    path=Path(f"{drive}:/$RECYCLE.BIN"),
                    description=f"Tempat sampah (Recycle Bin) di drive {drive}:.",
                    clean_contents_only=True,
                )
            )

    # 3. Browser Caches
    items.extend([
        SystemCacheItem(
            key="chrome_cache",
            name="Google Chrome Cache",
            category="Browser Caches",
            path=local_app_data / "Google" / "Chrome" / "User Data" / "Default" / "Cache",
            description="Cache penjelajahan web, gambar, dan media Google Chrome.",
            clean_contents_only=True,
        ),
        SystemCacheItem(
            key="chrome_code_cache",
            name="Google Chrome Code Cache",
            category="Browser Caches",
            path=local_app_data / "Google" / "Chrome" / "User Data" / "Default" / "Code Cache",
            description="Cache kompilasi JS/WASM Google Chrome.",
            clean_contents_only=True,
        ),
        SystemCacheItem(
            key="edge_cache",
            name="Microsoft Edge Cache",
            category="Browser Caches",
            path=local_app_data / "Microsoft" / "Edge" / "User Data" / "Default" / "Cache",
            description="Cache penjelajahan web dan media Microsoft Edge.",
            clean_contents_only=True,
        ),
        SystemCacheItem(
            key="edge_code_cache",
            name="Microsoft Edge Code Cache",
            category="Browser Caches",
            path=local_app_data / "Microsoft" / "Edge" / "User Data" / "Default" / "Code Cache",
            description="Cache kompilasi JS/WASM Microsoft Edge.",
            clean_contents_only=True,
        ),
        SystemCacheItem(
            key="brave_cache",
            name="Brave Browser Cache",
            category="Browser Caches",
            path=local_app_data / "BraveSoftware" / "Brave-Browser" / "User Data" / "Default" / "Cache",
            description="Cache penjelajahan web Brave Browser.",
            clean_contents_only=True,
        ),
    ])

    # 4. Developer Tools & Package Caches
    items.extend([
        SystemCacheItem(
            key="pip_cache",
            name="Pip Global Cache",
            category="Developer Tools",
            path=local_app_data / "pip" / "cache",
            description="Cache paket Python pip (.whl & tar.gz).",
            clean_command=[sys.executable, "-m", "pip", "cache", "purge"],
        ),
        SystemCacheItem(
            key="npm_cache",
            name="NPM Global Cache",
            category="Developer Tools",
            path=app_data / "npm-cache",
            description="Cache paket node_modules global npm (%APPDATA%\\npm-cache).",
            clean_command=["npm", "cache", "clean", "--force"],
        ),
        SystemCacheItem(
            key="yarn_cache",
            name="Yarn Cache",
            category="Developer Tools",
            path=local_app_data / "Yarn" / "Cache",
            description="Cache dependensi Yarn package manager.",
            clean_command=["yarn", "cache", "clean"],
        ),
        SystemCacheItem(
            key="pnpm_store",
            name="PNPM Global Store",
            category="Developer Tools",
            path=local_app_data / "pnpm" / "store",
            description="Penyimpanan dependensi global PNPM.",
        ),
        SystemCacheItem(
            key="composer_cache",
            name="Composer Global Cache",
            category="Developer Tools",
            path=local_app_data / "Composer",
            description="Cache paket pustaka PHP Composer (%LOCALAPPDATA%\\Composer).",
            clean_command=["composer", "clear-cache"],
        ),
        SystemCacheItem(
            key="gradle_cache",
            name="Gradle Global Cache",
            category="Developer Tools",
            path=home / ".gradle" / "caches",
            description="Cache dependensi build Android/Java Gradle (~/.gradle/caches).",
        ),
        SystemCacheItem(
            key="gradle_dists",
            name="Gradle Wrapper Distributions",
            category="Developer Tools",
            path=home / ".gradle" / "wrapper" / "dists",
            description="Arsip file zip Gradle wrapper lama (~/.gradle/wrapper/dists).",
        ),
        SystemCacheItem(
            key="nuget_cache",
            name="NuGet Global Packages Cache",
            category="Developer Tools",
            path=home / ".nuget" / "packages",
            description="Cache paket library .NET NuGet (~/.nuget/packages).",
            clean_command=["dotnet", "nuget", "locals", "all", "--clear"],
        ),
        SystemCacheItem(
            key="go_build_cache",
            name="Go Build Cache",
            category="Developer Tools",
            path=local_app_data / "go-build",
            description="Cache hasil kompilasi Go (%LOCALAPPDATA%\\go-build).",
            clean_command=["go", "clean", "-cache"],
        ),
        SystemCacheItem(
            key="go_mod_cache",
            name="Go Module Cache",
            category="Developer Tools",
            path=home / "go" / "pkg" / "mod",
            description="Cache unduhan modul pustaka Go (~/go/pkg/mod).",
            clean_command=["go", "clean", "-modcache"],
        ),
        SystemCacheItem(
            key="cargo_cache",
            name="Rust Cargo Cache",
            category="Developer Tools",
            path=home / ".cargo" / "registry" / "cache",
            description="Cache crate unduhan Rust (~/.cargo/registry/cache).",
        ),
        SystemCacheItem(
            key="vscode_cache",
            name="VS Code Cache",
            category="Developer Tools",
            path=app_data / "Code" / "Cache",
            description="Cache editor Visual Studio Code.",
            clean_contents_only=True,
        ),
        SystemCacheItem(
            key="vscode_cached_data",
            name="VS Code Cached V8 Data",
            category="Developer Tools",
            path=app_data / "Code" / "CachedData",
            description="Kompilasi kode V8 bytecode editor VS Code.",
            clean_contents_only=True,
        ),
        SystemCacheItem(
            key="gemini_backup",
            name="Antigravity / Gemini Backup",
            category="AI / Agent Backups",
            path=home / ".gemini" / "antigravity-backup",
            description="Cadangan file sesi lama Antigravity/Gemini.",
        ),
    ])

    return items


def get_macos_system_caches() -> List[SystemCacheItem]:
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
            clean_contents_only=True,
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
        SystemCacheItem(
            key="gradle_dists",
            name="Gradle Wrapper Distributions",
            category="Developer Tools",
            path=home / ".gradle" / "wrapper" / "dists",
            description="File zip rilis Gradle lama yang pernah diunduh projek (~/.gradle/wrapper/dists).",
        ),
        SystemCacheItem(
            key="go_cache",
            name="Go Build & Module Cache",
            category="Developer Tools",
            path=home / "go" / "pkg" / "mod",
            description="Cache download modul Go dan build cache (~/go/pkg/mod).",
            clean_command=["go", "clean", "-cache", "-modcache"],
        ),
        SystemCacheItem(
            key="xcode_sim_devices",
            name="Xcode Simulator Device Data",
            category="Developer Tools",
            path=home / "Library" / "Developer" / "CoreSimulator" / "Devices",
            description="Data dan memori internal simulator iOS iPhone/iPad.",
            clean_command=["xcrun", "simctl", "erase", "all"],
        ),
        SystemCacheItem(
            key="docker_cache",
            name="Docker VM & Containers",
            category="Developer Tools",
            path=home / "Library" / "Containers" / "com.docker.docker",
            description="Disk image dan container Docker Desktop.",
            clean_command=["docker", "system", "prune", "-a", "-f", "--volumes"],
        ),
    ]


def get_known_system_caches() -> List[SystemCacheItem]:
    """Return appropriate list of system caches depending on current OS."""
    if platform.system() == "Windows":
        return get_windows_system_caches()
    return get_macos_system_caches()


def scan_system_caches() -> List[SystemCacheItem]:
    """Scan and compute sizes for all existing system caches."""
    items = get_known_system_caches()
    active_items: List[SystemCacheItem] = []

    is_windows = platform.system() == "Windows"

    for item in items:
        # Check if item is a Windows Recycle Bin
        if is_windows and item.key.startswith("recycle_bin_"):
            drive_letter = item.key.split("_")[-1].upper()
            size, count = _get_windows_recycle_bin_info(drive_letter)
            if size > 0:
                item.size_bytes = size
                item.description = f"{count} item dalam Recycle Bin drive {drive_letter}:."
                active_items.append(item)
            continue

        if item.path.exists():
            item.size_bytes = get_path_size(item.path)
            # Report if greater than 10 MB (reduced threshold for visibility)
            if item.size_bytes > 10 * 1024 * 1024:
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

    is_windows = platform.system() == "Windows"

    # Handle Windows Recycle Bin emptying
    if is_windows and item.key.startswith("recycle_bin_"):
        drive_letter = item.key.split("_")[-1].upper()
        if dry_run:
            result.freed_bytes += item.size_bytes
            result.deleted_items.append(f"[DRY-RUN] Kosongkan Recycle Bin {drive_letter}:")
            return result

        success = _empty_windows_recycle_bin(drive_letter)
        if success:
            result.freed_bytes += item.size_bytes
            result.deleted_items.append(f"Recycle Bin {drive_letter}: dikosongkan")
            result.deleted_entries.append(
                DeletedEntry(
                    path=item.path,
                    relative_path=item.name,
                    size_bytes=item.size_bytes,
                    mode="permanent",
                    project_name=f"[SYSTEM] {item.name}",
                )
            )
        else:
            result.failed_items.append((item.name, "Gagal mengosongkan Recycle Bin"))
        return result

    if not item.path.exists():
        result.skipped_items.append(str(item.path))
        return result

    if dry_run:
        result.freed_bytes += item.size_bytes
        result.deleted_items.append(f"[DRY-RUN] {item.name}")
        return result

    # If item has a specific CLI tool clean command (e.g. npm cache clean, pip cache purge, composer clear-cache)
    if item.clean_command and shutil.which(item.clean_command[0]):
        try:
            cmd_proc = subprocess.run(
                item.clean_command,
                capture_output=True,
                text=True,
                timeout=45,
                check=False,
            )
            if cmd_proc.returncode == 0:
                result.commands_executed.append(" ".join(item.clean_command))
        except Exception:
            pass

    # If item is marked to clean contents only, or directory still exists
    if item.clean_contents_only and item.path.is_dir():
        freed = 0
        try:
            for child in item.path.iterdir():
                child_size = get_path_size(child)
                ok, _ = delete_target(child, use_trash=use_trash)
                if ok:
                    freed += child_size
        except Exception:
            pass

        result.freed_bytes += freed
        result.deleted_items.append(f"{item.name} ({format_size(freed)} dibersihkan)")
        result.deleted_entries.append(
            DeletedEntry(
                path=item.path,
                relative_path=item.name,
                size_bytes=freed,
                mode=deletion_mode,
                project_name=f"[SYSTEM] {item.name}",
            )
        )
        return result

    if item.path.exists():
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
        # Cleaned via command
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
