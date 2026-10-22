"""
Cleaner for Go / Golang projects.
"""

import shutil
import subprocess
from pathlib import Path
from typing import List, Optional

from ..models import CleanResult, CleanTarget, DeletedEntry, Project
from ..trash import delete_target
from ..utils import get_path_size
from .base import BaseCleaner


class GolangCleaner(BaseCleaner):
    @property
    def key(self) -> str:
        return "golang"

    @property
    def display_name(self) -> str:
        return "Go / Golang"

    def detect(self, project_path: Path) -> bool:
        return (project_path / "go.mod").is_file()

    def find_targets(self, project_path: Path, include_optional: bool = False) -> List[CleanTarget]:
        targets: List[CleanTarget] = []

        target_subpaths = [
            ("bin", True),
            ("dist", True),
            ("tmp", True),
            (".air_tmp", True),
            (".air-build", True),
            ("coverage.out", False),
        ]

        if include_optional:
            target_subpaths.append(("vendor", True))

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

        # Look for compiled executables matching directory name (e.g. app.exe or app)
        exe_names = [f"{project_path.name}.exe", project_path.name, "main.exe", "server.exe"]
        for exe in exe_names:
            exe_path = project_path / exe
            if exe_path.is_file():
                targets.append(
                    CleanTarget(
                        path=exe_path,
                        project_path=project_path,
                        size_bytes=get_path_size(exe_path),
                        is_dir=False,
                        target_type="executable",
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

        if prefer_cli and shutil.which("go"):
            if dry_run:
                result.commands_executed.append("[DRY-RUN] go clean")
            else:
                try:
                    cmd_proc = subprocess.run(
                        ["go", "clean"],
                        cwd=str(project.path),
                        capture_output=True,
                        text=True,
                        timeout=30,
                        check=False,
                    )
                    if cmd_proc.returncode == 0:
                        result.commands_executed.append("go clean")
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
