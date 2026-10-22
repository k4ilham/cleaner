"""
File logger for recording all deleted files, directories, commands, and freed disk space.
"""

from datetime import datetime
from pathlib import Path
from typing import Dict, Optional

from .models import CleanResult, format_size


class CleanerLogger:
    """Logs project cleaning operations to a .log file."""

    def __init__(self, log_path: Optional[Path] = None):
        if log_path is None:
            # Default to 'cleaner.log' in the project directory
            self.log_path = Path(__file__).parent.parent / "cleaner.log"
        else:
            self.log_path = Path(log_path).resolve()

        # Ensure parent directory exists
        self.log_path.parent.mkdir(parents=True, exist_ok=True)

    def log_session(
        self,
        target_dir: Path,
        results_by_project: Dict[str, CleanResult],
        use_trash: bool = False,
        dry_run: bool = False,
    ) -> Path:
        """
        Append a full session report to the .log file.
        Returns the Path to the log file written.
        """
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        mode_str = "DRY-RUN (Simulasi)" if dry_run else ("macOS Trash (Tempat Sampah)" if use_trash else "Permanent Delete")

        total_freed_bytes = sum(r.freed_bytes for r in results_by_project.values())
        total_items_deleted = sum(len(r.deleted_entries) for r in results_by_project.values())
        total_errors = sum(len(r.failed_items) for r in results_by_project.values())
        total_cmds = sum(len(r.commands_executed) for r in results_by_project.values())

        lines = []
        lines.append("=" * 80)
        lines.append(f"PROJECT CLEANER LOG - {now_str}")
        lines.append(f"Target Directory : {target_dir.resolve()}")
        lines.append(f"Deletion Mode    : {mode_str}")
        lines.append(f"Projects Cleaned : {len(results_by_project)}")
        lines.append("=" * 80)

        for proj_name, result in results_by_project.items():
            lines.append(f"\n[PROJECT] {proj_name}")

            for cmd in result.commands_executed:
                ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                lines.append(f"  [{ts}] [COMMAND] {cmd}")

            for entry in result.deleted_entries:
                ts = entry.timestamp.strftime("%Y-%m-%d %H:%M:%S")
                lines.append(
                    f"  [{ts}] [DELETED] {entry.path} | Size: {entry.formatted_size} | Mode: {entry.mode}"
                )

            # Fallback if deleted_entries was not populated
            if not result.deleted_entries and result.deleted_items:
                for item in result.deleted_items:
                    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    lines.append(f"  [{ts}] [DELETED] {item}")

            for item, err in result.failed_items:
                ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                lines.append(f"  [{ts}] [ERROR]   {item}: {err}")

        lines.append("\n" + "-" * 80)
        lines.append("SESSION SUMMARY:")
        lines.append(f"  - Total Space Freed : {format_size(total_freed_bytes)} ({total_freed_bytes:,} bytes)")
        lines.append(f"  - Items Cleaned     : {total_items_deleted}")
        lines.append(f"  - Commands Run      : {total_cmds}")
        lines.append(f"  - Errors            : {total_errors}")
        lines.append(f"  - Finished At       : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append("=" * 80 + "\n\n")

        with open(self.log_path, "a", encoding="utf-8") as f:
            f.write("\n".join(lines))

        return self.log_path

    def read_recent_lines(self, max_lines: int = 40) -> str:
        """Read the last N lines of the log file."""
        if not self.log_path.exists():
            return "File log belum dibuat atau masih kosong."
        try:
            with open(self.log_path, "r", encoding="utf-8") as f:
                all_lines = f.readlines()
                return "".join(all_lines[-max_lines:])
        except Exception as e:
            return f"Gagal membaca log: {e}"
