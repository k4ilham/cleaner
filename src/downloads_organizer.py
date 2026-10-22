"""
Downloads Folder Organizer & Cleaner for macOS.
Supports:
- Organizing files into smart categories (Documents, Images, Installers, Code, Archives, etc.)
- Detecting & cleaning junk files (.crdownload, .part, duplicates)
- Detecting large old installers (.dmg, .pkg)
- Complete Undo capability to restore moved files back to root
- Dry-run preview
"""

import hashlib
import json
import os
import shutil
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from .models import format_size
from .trash import delete_target


FILE_CATEGORIES: Dict[str, List[str]] = {
    "Documents": [
        ".pdf", ".docx", ".doc", ".txt", ".rtf", ".odt", ".pages", ".epub", ".md",
    ],
    "Spreadsheets": [
        ".xlsx", ".xls", ".csv", ".tsv", ".ods", ".numbers",
    ],
    "Presentations": [
        ".pptx", ".ppt", ".key", ".odp",
    ],
    "Images": [
        ".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp", ".bmp", ".ico", ".heic", ".raw", ".tiff", ".psd",
    ],
    "Installers": [
        ".dmg", ".pkg", ".iso", ".app",
    ],
    "Archives": [
        ".zip", ".tar", ".gz", ".tgz", ".7z", ".rar", ".bz2", ".xz",
    ],
    "Code & Developer": [
        ".sol", ".py", ".js", ".ts", ".jsx", ".tsx", ".html", ".css", ".dart",
        ".go", ".rs", ".java", ".cpp", ".c", ".sh", ".yaml", ".yml", ".json",
        ".xml", ".sql", ".env", ".prisma", ".proto",
    ],
    "Audio": [
        ".mp3", ".wav", ".m4a", ".aac", ".flac", ".ogg",
    ],
    "Video": [
        ".mp4", ".mov", ".mkv", ".avi", ".webm", ".flv",
    ],
}

JUNK_EXTENSIONS = {".crdownload", ".download", ".part", ".tmp"}


@dataclass
class MoveRecord:
    original_path: str
    current_path: str
    filename: str
    size_bytes: int
    timestamp: str


class DownloadsOrganizer:
    """Manages organizing and tidying up the user's Downloads folder."""

    def __init__(self, downloads_dir: Optional[Path] = None):
        self.downloads_dir = (downloads_dir or (Path.home() / "Downloads")).resolve()
        self.history_file = Path(__file__).parent.parent / "downloads_undo_history.json"

    def get_category_for_file(self, file_path: Path) -> str:
        """Determine folder category based on file extension."""
        ext = file_path.suffix.lower()
        for category, extensions in FILE_CATEGORIES.items():
            if ext in extensions:
                return category
        return "Others"

    def scan_downloads(self) -> Dict[str, List[Path]]:
        """
        Scan top-level files in Downloads and group them by category.
        Ignores folders and hidden files.
        """
        grouped: Dict[str, List[Path]] = {cat: [] for cat in FILE_CATEGORIES.keys()}
        grouped["Others"] = []
        grouped["Junk"] = []

        if not self.downloads_dir.exists():
            return grouped

        for entry in self.downloads_dir.iterdir():
            if entry.name.startswith("."):
                continue

            if entry.is_file():
                ext = entry.suffix.lower()
                if ext in JUNK_EXTENSIONS:
                    grouped["Junk"].append(entry)
                else:
                    cat = self.get_category_for_file(entry)
                    grouped[cat].append(entry)

        return grouped

    def find_duplicate_files(self) -> List[Tuple[Path, Path, int]]:
        """Find duplicate files in Downloads by comparing size and MD5."""
        duplicates: List[Tuple[Path, Path, int]] = []
        size_map: Dict[int, List[Path]] = {}

        if not self.downloads_dir.exists():
            return duplicates

        # Gather files
        for entry in self.downloads_dir.iterdir():
            if entry.name.startswith(".") or not entry.is_file():
                continue
            try:
                s = entry.stat().st_size
                if s > 0:
                    size_map.setdefault(s, []).append(entry)
            except Exception:
                continue

        # Check MD5 for files with identical size
        def get_md5(p: Path) -> str:
            h = hashlib.md5()
            with open(p, "rb") as f:
                while chunk := f.read(65536):
                    h.update(chunk)
            return h.hexdigest()

        for s, files in size_map.items():
            if len(files) > 1:
                seen_hashes: Dict[str, Path] = {}
                for f in files:
                    try:
                        f_hash = get_md5(f)
                        if f_hash in seen_hashes:
                            duplicates.append((seen_hashes[f_hash], f, s))
                        else:
                            seen_hashes[f_hash] = f
                    except Exception:
                        continue

        return duplicates

    def organize(self, dry_run: bool = False) -> List[MoveRecord]:
        """
        Move files into categorized subfolders.
        Records history to enable Undo.
        """
        grouped = self.scan_downloads()
        moves: List[MoveRecord] = []
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        for cat, files in grouped.items():
            if cat == "Junk" or not files:
                continue

            target_folder = self.downloads_dir / cat

            for file_path in files:
                dest_path = target_folder / file_path.name

                # Avoid overwriting existing files: append counter if needed
                if dest_path.exists() and dest_path != file_path:
                    stem = file_path.stem
                    suffix = file_path.suffix
                    counter = 1
                    while dest_path.exists():
                        dest_path = target_folder / f"{stem}_{counter}{suffix}"
                        counter += 1

                record = MoveRecord(
                    original_path=str(file_path.resolve()),
                    current_path=str(dest_path.resolve()),
                    filename=file_path.name,
                    size_bytes=file_path.stat().st_size,
                    timestamp=now_str,
                )
                moves.append(record)

                if not dry_run:
                    target_folder.mkdir(parents=True, exist_ok=True)
                    shutil.move(str(file_path), str(dest_path))

        if not dry_run and moves:
            self._save_undo_history(moves)

        return moves

    def clean_junk(self, dry_run: bool = False, use_trash: bool = True) -> List[Tuple[Path, int]]:
        """Remove incomplete downloads (.crdownload, .part) and temporary junk."""
        grouped = self.scan_downloads()
        junk_files = grouped.get("Junk", [])
        cleaned = []

        for f in junk_files:
            try:
                s = f.stat().st_size
                if not dry_run:
                    delete_target(f, use_trash=use_trash)
                cleaned.append((f, s))
            except Exception:
                continue

        return cleaned

    def undo_last_organization(self) -> Tuple[int, List[str]]:
        """
        Undo the last organization: move files back to their original root locations.
        """
        history = self._load_undo_history()
        if not history:
            return 0, ["Tidak ada riwayat perapian yang tersimpan."]

        last_session = history.pop()
        restored = 0
        errors = []

        for item in last_session:
            cur_p = Path(item["current_path"])
            orig_p = Path(item["original_path"])

            if cur_p.exists():
                try:
                    if orig_p.exists() and orig_p != cur_p:
                        # Append conflict suffix if root already has file with same name
                        orig_p = orig_p.parent / f"{orig_p.stem}_restored{orig_p.suffix}"
                    shutil.move(str(cur_p), str(orig_p))
                    restored += 1
                except Exception as e:
                    errors.append(f"{cur_p.name}: {e}")
            else:
                errors.append(f"{cur_p.name} tidak ditemukan di {cur_p}")

        # Remove empty category folders if left empty
        for cat in FILE_CATEGORIES.keys():
            cat_dir = self.downloads_dir / cat
            if cat_dir.is_dir() and not any(cat_dir.iterdir()):
                try:
                    cat_dir.rmdir()
                except Exception:
                    pass

        self._save_all_history(history)
        return restored, errors

    def _load_undo_history(self) -> List[List[dict]]:
        if not self.history_file.exists():
            return []
        try:
            with open(self.history_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []

    def _save_undo_history(self, moves: List[MoveRecord]):
        history = self._load_undo_history()
        history.append([asdict(m) for m in moves])
        # Keep last 5 sessions
        history = history[-5:]
        self._save_all_history(history)

    def _save_all_history(self, history: List[List[dict]]):
        try:
            with open(self.history_file, "w", encoding="utf-8") as f:
                json.dump(history, f, indent=2)
        except Exception:
            pass
