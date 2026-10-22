"""
Cleaner for PHP, Laravel, and Composer projects.
"""

import shutil
import subprocess
from pathlib import Path
from typing import List, Optional

from ..models import CleanResult, CleanTarget, DeletedEntry, Project
from ..trash import delete_target
from ..utils import get_path_size
from .base import BaseCleaner


class PHPCleaner(BaseCleaner):
    @property
    def key(self) -> str:
        return "php"

    @property
    def display_name(self) -> str:
        return "PHP / Laravel / Composer"

    def detect(self, project_path: Path) -> bool:
        return (project_path / "composer.json").is_file()

    def find_targets(self, project_path: Path, include_optional: bool = False) -> List[CleanTarget]:
        targets: List[CleanTarget] = []

        # Standard cache and temp paths in Laravel / Symfony / PHP projects
        target_subpaths = [
            ("node_modules", True),
            ("public/build", True),
            ("storage/logs", True),
            ("storage/framework/cache", True),
            ("storage/framework/views", True),
            ("storage/framework/sessions", True),
            ("bootstrap/cache", True),
            (".phpunit.cache", True),
            ("var/cache", True),
            ("var/log", True),
            (".php-cs-fixer.cache", False),
        ]

        if include_optional:
            target_subpaths.append(("vendor", True))

        for subpath, is_dir in target_subpaths:
            path = project_path / subpath
            if path.exists() or path.is_symlink():
                # For storage folders, we want to know if there's actual data inside
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
        artisan_file = project.path / "artisan"

        if prefer_cli and artisan_file.is_file() and shutil.which("php"):
            if dry_run:
                result.commands_executed.append("[DRY-RUN] php artisan optimize:clear")
            else:
                try:
                    cmd_proc = subprocess.run(
                        ["php", "artisan", "optimize:clear"],
                        cwd=str(project.path),
                        capture_output=True,
                        text=True,
                        timeout=40,
                        check=False,
                    )
                    if cmd_proc.returncode == 0:
                        result.commands_executed.append("php artisan optimize:clear")
                except Exception:
                    pass

        # Clean individual directory targets
        for t in targets:
            if not t.path.exists() and not t.path.is_symlink():
                result.skipped_items.append(t.relative_path)
                continue

            # For Laravel storage subdirectories, preserve directory structure (.gitignore) if possible
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
                # Re-create empty directory for storage folders so Laravel doesn't crash on next run
                if t.is_dir and "storage" in t.relative_path:
                    try:
                        t.path.mkdir(parents=True, exist_ok=True)
                        gitignore = t.path / ".gitignore"
                        if not gitignore.exists():
                            gitignore.write_text("*\n!.gitignore\n")
                    except Exception:
                        pass
            else:
                result.failed_items.append((t.relative_path, error))

        return result
