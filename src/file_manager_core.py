"""
Core engine for File Manager & Large Disk Usage Analyzer.
Provides high-performance directory scanning, size calculation,
large file deep search, disk space monitoring, and safe deletion.
"""

import os
import platform
import shutil
import stat
import subprocess
import time
from datetime import datetime
from pathlib import Path
from typing import Callable, Optional
import psutil

# Safe trash handler using native Windows Recycle Bin API
from src.trash import send_to_trash, _handle_remove_readonly


# File category definitions based on extensions
CATEGORY_MAP = {
    "Video": {".mp4", ".mkv", ".avi", ".mov", ".wmv", ".flv", ".webm", ".m4v", ".ts", ".vob"},
    "Audio": {".mp3", ".wav", ".flac", ".aac", ".ogg", ".wma", ".m4a", ".opus"},
    "Archive / ISO": {".zip", ".rar", ".7z", ".tar", ".gz", ".bz2", ".xz", ".iso", ".img", ".dmg", ".tgz"},
    "Installer / Executable": {".exe", ".msi", ".bat", ".cmd", ".ps1", ".vbs", ".app", ".pkg", ".deb", ".rpm"},
    "Disk / VM": {".vmdk", ".vdi", ".vhd", ".vhdx", ".qcow2"},
    "Document": {".pdf", ".docx", ".doc", ".xlsx", ".xls", ".pptx", ".ppt", ".txt", ".csv", ".rtf", ".odt"},
    "Image": {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp", ".svg", ".tiff", ".ico", ".raw"},
    "Database": {".sql", ".sqlite", ".sqlite3", ".db", ".mdb", ".accdb", ".frm", ".ibd"},
    "Code / Dev": {".py", ".js", ".ts", ".html", ".css", ".java", ".cpp", ".c", ".cs", ".go", ".rs", ".php", ".json", ".xml", ".yaml", ".yml"},
}


def format_bytes(size_bytes: int) -> str:
    """Format bytes into readable string (B, KB, MB, GB, TB)."""
    if size_bytes < 0:
        return "0 B"
    units = ["B", "KB", "MB", "GB", "TB", "PB"]
    val = float(size_bytes)
    unit_index = 0
    while val >= 1024.0 and unit_index < len(units) - 1:
        val /= 1024.0
        unit_index += 1
    if unit_index == 0:
        return f"{int(val)} B"
    return f"{val:.2f} {units[unit_index]}"


def parse_size_str(size_str: str) -> int:
    """Parse string like '100MB', '1.5GB', '500KB' into bytes."""
    size_str = size_str.strip().upper()
    multiplier = 1
    if size_str.endswith("TB"):
        multiplier = 1024 ** 4
        num = size_str[:-2]
    elif size_str.endswith("GB"):
        multiplier = 1024 ** 3
        num = size_str[:-2]
    elif size_str.endswith("MB"):
        multiplier = 1024 ** 2
        num = size_str[:-2]
    elif size_str.endswith("KB"):
        multiplier = 1024
        num = size_str[:-2]
    elif size_str.endswith("B"):
        multiplier = 1
        num = size_str[:-1]
    else:
        num = size_str

    try:
        return int(float(num) * multiplier)
    except ValueError:
        return 0


def get_file_category(extension: str) -> str:
    """Classify file extension into a friendly category."""
    ext = extension.lower()
    for category, extensions in CATEGORY_MAP.items():
        if ext in extensions:
            return category
    return "Lainnya" if ext else "File Tanpa Ekstensi"


def get_drive_info(path_or_drive: str) -> dict:
    """Get total, used, free space and usage percentage for the given path/drive."""
    try:
        usage = psutil.disk_usage(path_or_drive)
        is_critical = usage.percent >= 90.0 or (usage.free < 20 * (1024 ** 3))
        is_warning = usage.percent >= 80.0
        return {
            "total": usage.total,
            "used": usage.used,
            "free": usage.free,
            "percent": usage.percent,
            "total_str": format_bytes(usage.total),
            "used_str": format_bytes(usage.used),
            "free_str": format_bytes(usage.free),
            "is_critical": is_critical,
            "is_warning": is_warning,
        }
    except Exception as e:
        return {
            "total": 0,
            "used": 0,
            "free": 0,
            "percent": 0.0,
            "total_str": "0 B",
            "used_str": "0 B",
            "free_str": "0 B",
            "is_critical": False,
            "is_warning": False,
            "error": str(e),
        }


def get_available_drives() -> list[str]:
    """Return available partition drive root paths (e.g. ['C:\\', 'D:\\'])."""
    drives = []
    try:
        for part in psutil.disk_partitions(all=False):
            if part.mountpoint:
                drives.append(part.mountpoint)
    except Exception:
        drives = ["C:\\"]
    return sorted(list(set(drives)))


def is_reparse_point_or_system(entry: os.DirEntry) -> bool:
    """Check if entry is an NTFS Junction / Reparse Point or desktop.ini to protect Windows special folders."""
    try:
        stat_res = entry.stat(follow_symlinks=False)
        attrs = getattr(stat_res, "st_file_attributes", 0)
        FILE_ATTRIBUTE_REPARSE_POINT = 0x0400
        if attrs & FILE_ATTRIBUTE_REPARSE_POINT:
            return True
    except Exception:
        pass
    return False


def get_folder_fast_items(folder_path: Path) -> list[dict]:
    """
    Fast non-recursive scan of the current directory.
    Files get immediate exact size; folders are listed with size 0 pending background calculation.
    """
    items = []
    if not folder_path.exists() or not folder_path.is_dir():
        return items

    try:
        with os.scandir(folder_path) as entries:
            for entry in entries:
                try:
                    is_symlink = entry.is_symlink()
                    is_reparse = is_reparse_point_or_system(entry)
                    stat_res = entry.stat(follow_symlinks=False)
                    mtime = datetime.fromtimestamp(stat_res.st_mtime).strftime("%Y-%m-%d %H:%M:%S")

                    if entry.is_dir(follow_symlinks=False):
                        items.append({
                            "name": entry.name,
                            "path": str(Path(entry.path).resolve()),
                            "is_dir": True,
                            "is_reparse": is_reparse,
                            "size": 0,
                            "size_str": "Menghitung...",
                            "items_count": "-",
                            "mtime": mtime,
                            "category": "Folder",
                            "extension": "",
                        })
                    else:
                        size = stat_res.st_size
                        ext = Path(entry.name).suffix.lower()
                        items.append({
                            "name": entry.name,
                            "path": str(Path(entry.path).resolve()),
                            "is_dir": False,
                            "is_reparse": is_reparse,
                            "size": size,
                            "size_str": format_bytes(size),
                            "items_count": "1 file",
                            "mtime": mtime,
                            "category": get_file_category(ext),
                            "extension": ext,
                        })
                except (PermissionError, OSError):
                    continue
    except (PermissionError, OSError):
        pass

    return items


def calculate_folder_size(folder_path: Path, cancel_check: Optional[Callable[[], bool]] = None) -> tuple[int, int]:
    """
    Calculates the total size and file count of a directory recursively.
    Skips NTFS junctions and symlinks to avoid infinite loops or permission locks.
    """
    total_size = 0
    total_files = 0
    stack = [str(folder_path)]

    while stack:
        if cancel_check and cancel_check():
            break
        current_dir = stack.pop()
        try:
            with os.scandir(current_dir) as entries:
                for entry in entries:
                    if cancel_check and cancel_check():
                        break
                    try:
                        if entry.is_symlink() or is_reparse_point_or_system(entry):
                            continue
                        if entry.is_file(follow_symlinks=False):
                            total_size += entry.stat(follow_symlinks=False).st_size
                            total_files += 1
                        elif entry.is_dir(follow_symlinks=False):
                            stack.append(entry.path)
                    except (PermissionError, OSError):
                        continue
        except (PermissionError, OSError):
            continue

    return total_size, total_files


def scan_largest_files(
    root_path: Path,
    min_size_bytes: int = 10 * 1024 * 1024,
    max_results: int = 100,
    progress_callback: Optional[Callable[[int, int, str], None]] = None,
    cancel_check: Optional[Callable[[], bool]] = None,
) -> list[dict]:
    """
    Deep scan a folder and its subdirectories to locate the largest files.
    
    Args:
        root_path: Directory to scan
        min_size_bytes: Minimum file size to include (default 10 MB)
        max_results: Maximum number of files to return
        progress_callback: callback(scanned_files, found_files, current_folder_str)
        cancel_check: function returning True if scan should abort
        
    Returns:
        List of dicts sorted by size descending.
    """
    found_files = []
    scanned_count = 0
    last_progress_time = time.time()

    stack = [str(root_path)]

    while stack:
        if cancel_check and cancel_check():
            break
        current_dir = stack.pop()

        if progress_callback and (time.time() - last_progress_time > 0.15):
            progress_callback(scanned_count, len(found_files), os.path.basename(current_dir) or current_dir)
            last_progress_time = time.time()

        try:
            with os.scandir(current_dir) as entries:
                for entry in entries:
                    if cancel_check and cancel_check():
                        break
                    try:
                        if entry.is_symlink() or is_reparse_point_or_system(entry):
                            continue

                        if entry.is_file(follow_symlinks=False):
                            scanned_count += 1
                            stat_res = entry.stat(follow_symlinks=False)
                            size = stat_res.st_size
                            if size >= min_size_bytes:
                                ext = Path(entry.name).suffix.lower()
                                mtime = datetime.fromtimestamp(stat_res.st_mtime).strftime("%Y-%m-%d %H:%M:%S")
                                found_files.append({
                                    "name": entry.name,
                                    "path": str(Path(entry.path).resolve()),
                                    "folder": current_dir,
                                    "size": size,
                                    "size_str": format_bytes(size),
                                    "category": get_file_category(ext),
                                    "extension": ext,
                                    "mtime": mtime,
                                })
                        elif entry.is_dir(follow_symlinks=False):
                            stack.append(entry.path)
                    except (PermissionError, OSError):
                        continue
        except (PermissionError, OSError):
            continue

    # Sort descending by size
    found_files.sort(key=lambda x: x["size"], reverse=True)
    if max_results and max_results > 0:
        found_files = found_files[:max_results]

    if progress_callback:
        progress_callback(scanned_count, len(found_files), "Selesai")

    return found_files


def delete_item(path: Path, use_recycle_bin: bool = True) -> tuple[bool, str]:
    """
    Delete a single file or directory.
    
    Args:
        path: Path to target
        use_recycle_bin: If True, moves to Windows Recycle Bin. If False, deletes permanently.
        
    Returns:
        tuple (success: bool, error_message: str)
    """
    if not path.exists() and not path.is_symlink():
        return False, "Berkas atau folder tidak ditemukan."

    # Prevent deleting protected system files like desktop.ini in user root
    if path.name.lower() == "desktop.ini" and path.parent in [Path.home(), Path.home() / "Downloads", Path.home() / "Documents"]:
        return False, "File sistem desktop.ini dilindungi untuk mencegah rusaknya folder khusus Windows."

    if use_recycle_bin:
        success = send_to_trash(path)
        if success:
            return True, ""
        # If recycle bin failed or unsupported, we don't automatically fall back to permanent delete
        # without explicit user request.
        return False, "Gagal memindahkan ke Recycle Bin. Anda dapat memilih opsi Hapus Permanen jika diinginkan."

    # Permanent deletion
    try:
        if path.is_file() or path.is_symlink():
            try:
                os.chmod(path, stat.S_IWRITE | stat.S_IREAD)
            except Exception:
                pass
            path.unlink()
        elif path.is_dir():
            shutil.rmtree(path, onerror=_handle_remove_readonly)
        return True, ""
    except Exception as e:
        return False, str(e)


def delete_multiple(
    paths: list[Path],
    use_recycle_bin: bool = True,
    progress_cb: Optional[Callable[[int, int, str], None]] = None,
) -> dict:
    """
    Delete multiple files or folders.
    
    Returns:
        dict: {
            "success_count": int,
            "failed_count": int,
            "freed_bytes": int,
            "errors": list[tuple[str, str]]
        }
    """
    success_count = 0
    failed_count = 0
    freed_bytes = 0
    errors = []

    total = len(paths)
    for idx, path in enumerate(paths):
        if progress_cb:
            progress_cb(idx + 1, total, path.name)

        item_size = 0
        try:
            if path.is_file():
                item_size = path.stat().st_size
            elif path.is_dir():
                s, _ = calculate_folder_size(path)
                item_size = s
        except Exception:
            pass

        ok, err = delete_item(path, use_recycle_bin=use_recycle_bin)
        if ok:
            success_count += 1
            freed_bytes += item_size
        else:
            failed_count += 1
            errors.append((str(path), err))

    return {
        "success_count": success_count,
        "failed_count": failed_count,
        "freed_bytes": freed_bytes,
        "freed_str": format_bytes(freed_bytes),
        "errors": errors,
    }


def reveal_in_explorer(path: Path) -> bool:
    """Open Windows Explorer and highlight the selected file or open folder."""
    try:
        resolved = str(path.resolve())
        if platform.system() == "Windows":
            if path.is_file():
                subprocess.Popen(f'explorer /select,"{resolved}"')
            else:
                subprocess.Popen(f'explorer "{resolved}"')
            return True
        elif platform.system() == "Darwin":
            subprocess.Popen(["open", "-R", resolved])
            return True
        else:
            subprocess.Popen(["xdg-open", str(path.parent if path.is_file() else path)])
            return True
    except Exception:
        return False


def open_default_app(path: Path) -> bool:
    """Open file with its default registered system application."""
    try:
        resolved = str(path.resolve())
        if platform.system() == "Windows":
            os.startfile(resolved)
            return True
        elif platform.system() == "Darwin":
            subprocess.Popen(["open", resolved])
            return True
        else:
            subprocess.Popen(["xdg-open", resolved])
            return True
    except Exception:
        return False

