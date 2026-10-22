"""
Cleaner for .NET and C# projects.
"""

import shutil
import subprocess
from pathlib import Path
from typing import List, Optional

from ..models import CleanResult, CleanTarget, DeletedEntry, Project
from ..trash import delete_target
from ..utils import get_path_size
from .base import BaseCleaner


class DotNetCleaner(BaseCleaner):
    @property
    def key(self) -> str:
        return "dotnet"

    @property
    def display_name(self) -> str:
        return ".NET / C#"

    def detect(self, project_path: Path) -> bool:
        try:
            for item in project_path.iterdir():
                if item.is_file() and (item.suffix in {".csproj", ".fsproj", ".sln", ".vbproj"}):
                    return True
        except (PermissionError, OSError):
            pass
        return False

    def find_targets(self, project_path: Path, include_optional: bool = False) -> List[CleanTarget]:
        targets: List[CleanTarget] = []

        target_subpaths = [
            ("bin", True),
            ("obj", True),
            (".vs", True),
            ("TestResults", True),
        ]

        for subpath, is_dir in target_subpaths:
            path = project_path / subpath
            if path.exists() or path.is_symlink():
                size = get_path_size(path)
                if size > 0 or path.is_dir() or path.is_symlink():
                    targets.append(
                        CleanTarget(
                            path=path,
                            project_path=project_path,
                            size_bytes=size,
                            is_dir=is_dir,
                            target_type=subpath,
                        )
                    )

        return targets

    def execute_clean(
        self,
        project: Project,
        targets: List[CleanTarget],
        dry_run: bool = False,
        use_trash: bool = False,
        prefer_cli: bool = True,
    ) -> CleanResult:
        result = CleanResult()

        if prefer_cli and shutil.which("dotnet"):
            if dry_run:
                result.commands_executed.append("[DRY-RUN] dotnet clean")
            else:
                try:
                    cmd_proc = subprocess.run(
                        ["dotnet", "clean", "-v", "q"],
                        cwd=str(project.path),
                        capture_output=True,
                        text=True,
                        timeout=30,
                        check=False,
                    )
                    if cmd_proc.returncode == 0:
                        result.commands_executed.append("dotnet clean")
                except Exception:
                    pass

        for t in targets:
            if not t.path.exists() and not t.path.is_symlink():
                result.skipped_items.append(t.relative_path)
                continue

            if dry_run:
                result.freed_bytes += t.size_bytes
                result.deleted_items.append(f"[DRY-RUN] {t.relative_path}")
                continue

            success, error = delete_target(t.path, use_trash=use_trash)
            if success:
                result.freed_bytes += t.size_bytes
                result.deleted_items.append(t.relative_path)
                result.deleted_entries.append(
                    DeletedEntry(
                        path=t.path,
                        relative_path=t.relative_path,
                        size_bytes=t.size_bytes,
                        mode="trash" if use_trash else "permanent",
                        project_name=project.name,
                    )
                )
            else:
                result.failed_items.append((t.relative_path, error))

        return result
