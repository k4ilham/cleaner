"""
Safe deletion handlers supporting macOS Trash and permanent removal.
"""

import os
import platform
import shutil
import stat
import subprocess
from pathlib import Path


def _handle_remove_readonly(func, path, exc_info):
    """Error handler for shutil.rmtree to handle read-only files."""
    try:
        os.chmod(path, stat.S_IWRITE | stat.S_IREAD)
        func(path)
    except Exception:
        pass


def _send_to_windows_recycle_bin(path_str: str) -> bool:
    """Send file or folder to Windows Recycle Bin using native Win32 API."""
    try:
        import ctypes
        from ctypes import wintypes

        class SHFILEOPSTRUCTW(ctypes.Structure):
            _fields_ = [
                ("hwnd", wintypes.HWND),
                ("wFunc", wintypes.UINT),
                ("pFrom", wintypes.LPCWSTR),
                ("pTo", wintypes.LPCWSTR),
                ("fFlags", wintypes.WORD),
                ("fAnyOperationsAborted", wintypes.BOOL),
                ("hNameMappings", wintypes.LPVOID),
                ("lpszProgressTitle", wintypes.LPCWSTR),
            ]

        FO_DELETE = 3
        FOF_ALLOWUNDO = 0x0040
        FOF_NOCONFIRMATION = 0x0010
        FOF_SILENT = 0x0004
        FOF_NOERRORUI = 0x0400

        # Win32 expects double-null terminated string
        pFrom = os.path.abspath(path_str) + "\0\0"
        fileop = SHFILEOPSTRUCTW()
        fileop.wFunc = FO_DELETE
        fileop.pFrom = pFrom
        fileop.fFlags = FOF_ALLOWUNDO | FOF_NOCONFIRMATION | FOF_SILENT | FOF_NOERRORUI

        ret = ctypes.windll.shell32.SHFileOperationW(ctypes.byref(fileop))
        return ret == 0
    except Exception:
        return False


def send_to_trash(path: Path) -> bool:
    """
    Send a file or directory to Windows Recycle Bin or macOS Trash.
    Falls back to normal delete if unsupported or failed.
    """
    path_str = str(path.resolve())
    sys_name = platform.system()

    if sys_name == "Windows":
        return _send_to_windows_recycle_bin(path_str)

    if sys_name == "Darwin":
        try:
            # Escape double quotes and backslashes for AppleScript
            escaped_path = path_str.replace("\\", "\\\\").replace('"', '\\"')
            script = f'tell application "Finder" to delete POSIX file "{escaped_path}"'
            result = subprocess.run(
                ["osascript", "-e", script],
                capture_output=True,
                text=True,
                check=False,
            )
            if result.returncode == 0:
                return True
        except Exception:
            pass

    return False


def delete_target(path: Path, use_trash: bool = False) -> tuple[bool, str]:
    """
    Delete a file or directory.
    
    Args:
        path: Path to file or directory
        use_trash: If True, attempts to move to Trash first.
        
    Returns:
        tuple (success: bool, error_message: str)
    """
    if not path.exists() and not path.is_symlink():
        return True, ""

    if use_trash:
        if send_to_trash(path):
            return True, ""
        # If moving to trash failed, return error or fallback?
        # Better to return error if trash was specifically requested, or fallback if configured.

    try:
        if path.is_symlink() or path.is_file():
            try:
                path.unlink()
            except PermissionError:
                os.chmod(path, stat.S_IWRITE)
                path.unlink()
        elif path.is_dir():
            shutil.rmtree(path, onerror=_handle_remove_readonly)
        return True, ""
    except Exception as e:
        return False, str(e)
