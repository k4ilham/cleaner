"""
Cleaner for Flutter and Dart projects.
"""

import shutil
import subprocess
from pathlib import Path
from typing import List, Optional

from ..models import CleanResult, CleanTarget, DeletedEntry, Project
from ..trash import delete_target
from ..utils import get_path_size
from .base import BaseCleaner


class FlutterCleaner(BaseCleaner):
    @property
    def key(self) -> str:
        return "flutter"

    @property
    def display_name(self) -> str:
        return "Flutter / Dart"

    def detect(self, project_path: Path) -> bool:
        pubspec = project_path / "pubspec.yaml"
        return pubspec.is_file()

    def find_targets(self, project_path: Path, include_optional: bool = False) -> List[CleanTarget]:
        targets: List[CleanTarget] = []
        
        target_subpaths = [
            ("build", True),
            (".dart_tool", True),
            (".flutter-plugins", False),
            (".flutter-plugins-dependencies", False),
            ("android/.gradle", True),
            ("android/app/build", True),
            ("ios/Pods", True),
            ("ios/.symlinks", True),
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
        targets: Optional[List[CleanTarget]] = None,
        dry_run: bool = False,
        use_trash: bool = False,
        prefer_cli: bool = True,
    ) -> CleanResult:
        result = CleanResult()
        has_flutter_cli = shutil.which("flutter") is not None
        deletion_mode = "trash" if use_trash else "permanent"

        # Try running `flutter clean` if preferred and available
        if prefer_cli and has_flutter_cli and not dry_run:
            try:
                cmd_proc = subprocess.run(
                    ["flutter", "clean"],
                    cwd=str(project.path),
                    capture_output=True,
                    text=True,
                    timeout=45,
                    check=False,
                )
                if cmd_proc.returncode == 0:
                    result.commands_executed.append("flutter clean")
                else:
                    result.failed_items.append(("flutter clean", cmd_proc.stderr.strip()[:100]))
            except Exception as e:
                result.failed_items.append(("flutter clean", str(e)[:100]))

        # Delete any remaining targets
        targets_to_clean = targets if targets is not None else project.targets
        for target in targets_to_clean:
            if not target.path.exists() and not target.path.is_symlink():
                # Already cleaned by flutter clean
                result.freed_bytes += target.size_bytes
                if target.relative_to_project not in result.deleted_items:
                    result.deleted_items.append(f"{target.relative_to_project} (via flutter clean)")
                    result.deleted_entries.append(
                        DeletedEntry(
                            path=target.path,
                            relative_path=target.relative_to_project,
                            size_bytes=target.size_bytes,
                            mode="flutter clean",
                            project_name=project.name,
                        )
                    )
                continue

            if dry_run:
                result.freed_bytes += target.size_bytes
                result.deleted_items.append(f"[DRY-RUN] {target.relative_to_project}")
            else:
                success, error = delete_target(target.path, use_trash=use_trash)
                if success:
                    result.freed_bytes += target.size_bytes
                    result.deleted_items.append(target.relative_to_project)
                    result.deleted_entries.append(
                        DeletedEntry(
                            path=target.path,
                            relative_path=target.relative_to_project,
                            size_bytes=target.size_bytes,
                            mode=deletion_mode,
                            project_name=project.name,
                        )
                    )
                else:
                    result.failed_items.append((target.relative_to_project, error))

        return result
