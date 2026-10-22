"""
Cleaner for Xcode, Swift, and iOS/macOS projects.
"""

from pathlib import Path
from typing import List

from ..models import CleanTarget
from ..utils import get_path_size
from .base import BaseCleaner


class XcodeCleaner(BaseCleaner):
    @property
    def key(self) -> str:
        return "xcode"

    @property
    def display_name(self) -> str:
        return "Xcode / iOS / macOS"

    def detect(self, project_path: Path) -> bool:
        # Avoid treating Flutter project ios subfolder as standalone
        if (project_path / "pubspec.yaml").is_file():
            return False

        if (project_path / "Podfile").is_file() or (project_path / "Package.swift").is_file():
            return True

        # Check for .xcodeproj or .xcworkspace
        try:
            for item in project_path.iterdir():
                if item.suffix in {".xcodeproj", ".xcworkspace"}:
                    return True
        except (OSError, PermissionError):
            pass

        return False

    def find_targets(self, project_path: Path, include_optional: bool = False) -> List[CleanTarget]:
        targets: List[CleanTarget] = []
        target_subpaths = [
            ("Pods", True),
            ("DerivedData", True),
            (".build", True),
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
