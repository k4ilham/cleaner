"""
Cleaner for Gradle and Android native projects.
"""

from pathlib import Path
from typing import List

from ..models import CleanTarget
from ..utils import get_path_size
from .base import BaseCleaner


class GradleCleaner(BaseCleaner):
    @property
    def key(self) -> str:
        return "gradle"

    @property
    def display_name(self) -> str:
        return "Gradle / Android"

    def detect(self, project_path: Path) -> bool:
        # Avoid treating Flutter project android subfolder as standalone unless standalone
        if (project_path / "pubspec.yaml").is_file():
            return False

        markers = ["build.gradle", "build.gradle.kts", "settings.gradle", "settings.gradle.kts", "gradlew"]
        for marker in markers:
            if (project_path / marker).is_file():
                return True
        return False

    def find_targets(self, project_path: Path, include_optional: bool = False) -> List[CleanTarget]:
        targets: List[CleanTarget] = []
        target_subpaths = [
            (".gradle", True),
            ("build", True),
            ("app/build", True),
            (".kotlin", True),
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
