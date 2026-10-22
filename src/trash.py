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


def send_to_trash(path: Path) -> bool:
    """
    Send a file or directory to macOS Trash using AppleScript.
    Falls back to normal delete if unsupported or failed.
    """
    path_str = str(path.resolve())
    if platform.system() == "Darwin":
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
