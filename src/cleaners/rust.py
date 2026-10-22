"""
Cleaner for Rust projects (target directory).
"""

import shutil
import subprocess
from pathlib import Path
from typing import List, Optional

from ..models import CleanResult, CleanTarget, Project
from ..trash import delete_target
from ..utils import get_path_size
from .base import BaseCleaner


class RustCleaner(BaseCleaner):
    @property
    def key(self) -> str:
        return "rust"

    @property
    def display_name(self) -> str:
        return "Rust / Cargo"

    def detect(self, project_path: Path) -> bool:
        return (project_path / "Cargo.toml").is_file()

    def find_targets(self, project_path: Path, include_optional: bool = False) -> List[CleanTarget]:
        targets: List[CleanTarget] = []
        target_path = project_path / "target"

        if target_path.exists() or target_path.is_symlink():
            size = get_path_size(target_path)
            if size > 0 or target_path.is_dir():
                targets.append(
                    CleanTarget(
                        path=target_path,
                        project_path=project_path,
                        size_bytes=size,
                        is_dir=True,
                        target_type="target",
                    )
                )

        return targets

    def execute_clean(
        self,
        project: Project,
        targets: Optional[List[CleanTarget]] = None,
        dry_run: bool = False,
        use_trash: bool = False,
        prefer_cli: bool = True,
    ) -> CleanResult:
        result = CleanResult()
        has_cargo = shutil.which("cargo") is not None

        if prefer_cli and has_cargo and not dry_run:
            try:
                cmd_proc = subprocess.run(
                    ["cargo", "clean"],
                    cwd=str(project.path),
                    capture_output=True,
                    text=True,
                    timeout=30,
                    check=False,
                )
                if cmd_proc.returncode == 0:
                    result.commands_executed.append("cargo clean")
            except Exception:
                pass

        targets_to_clean = targets if targets is not None else project.targets
        for target in targets_to_clean:
            if not target.path.exists() and not target.path.is_symlink():
                result.freed_bytes += target.size_bytes
                if target.relative_to_project not in result.deleted_items:
                    result.deleted_items.append(f"{target.relative_to_project} (via cargo clean)")
                continue

            if dry_run:
                result.freed_bytes += target.size_bytes
                result.deleted_items.append(f"[DRY-RUN] {target.relative_to_project}")
            else:
                success, error = delete_target(target.path, use_trash=use_trash)
                if success:
                    result.freed_bytes += target.size_bytes
                    result.deleted_items.append(target.relative_to_project)
                else:
                    result.failed_items.append((target.relative_to_project, error))

        return result
