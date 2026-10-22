"""
Base cleaner class and interface.
"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import List, Optional

from ..models import CleanResult, CleanTarget, DeletedEntry, Project
from ..trash import delete_target


class BaseCleaner(ABC):
    """Abstract base class for ecosystem-specific project cleaners."""

    @property
    @abstractmethod
    def key(self) -> str:
        """Unique key identifying this cleaner (e.g., 'flutter', 'node')."""
        pass

    @property
    @abstractmethod
    def display_name(self) -> str:
        """User-friendly name (e.g., 'Flutter / Dart')."""
        pass

    @abstractmethod
    def detect(self, project_path: Path) -> bool:
        """Return True if this directory is a project of this type."""
        pass

    @abstractmethod
    def find_targets(self, project_path: Path, include_optional: bool = False) -> List[CleanTarget]:
        """Find cleanable directories and files for this project."""
        pass

    def execute_clean(
        self,
        project: Project,
        targets: Optional[List[CleanTarget]] = None,
        dry_run: bool = False,
        use_trash: bool = False,
        prefer_cli: bool = True,
    ) -> CleanResult:
        """
        Clean the project targets. Subclasses may override to run CLI commands (e.g. flutter clean).
        """
        result = CleanResult()
        targets_to_clean = targets if targets is not None else project.targets
        deletion_mode = "trash" if use_trash else "permanent"

        for target in targets_to_clean:
            if not target.path.exists() and not target.path.is_symlink():
                result.skipped_items.append(str(target.path))
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
