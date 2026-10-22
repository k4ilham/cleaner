"""
Cleaner for Python projects (caches, build artifacts, and optional virtualenvs).
"""

import os
from pathlib import Path
from typing import List

from ..models import CleanTarget
from ..utils import get_path_size
from .base import BaseCleaner


class PythonCleaner(BaseCleaner):
    @property
    def key(self) -> str:
        return "python"

    @property
    def display_name(self) -> str:
        return "Python"

    def detect(self, project_path: Path) -> bool:
        markers = [
            "pyproject.toml",
            "requirements.txt",
            "setup.py",
            "setup.cfg",
            "Pipfile",
            "environment.yml",
            "manage.py",
        ]
        for marker in markers:
            if (project_path / marker).is_file():
                return True
        return False

    def find_targets(self, project_path: Path, include_optional: bool = False) -> List[CleanTarget]:
        targets: List[CleanTarget] = []
        seen_paths = set()

        # Fixed top-level targets
        static_targets = [
            (".pytest_cache", True, False),
            (".mypy_cache", True, False),
            (".ruff_cache", True, False),
            (".coverage", False, False),
            ("htmlcov", True, False),
            (".tox", True, False),
            ("build", True, False),
            ("dist", True, False),
        ]

        # Optional venv targets
        if include_optional:
            static_targets.extend([
                (".venv", True, True),
                ("venv", True, True),
                ("env", True, True),
            ])

        for subpath, is_dir, is_opt in static_targets:
            path = project_path / subpath
            if (path.exists() or path.is_symlink()) and path not in seen_paths:
                seen_paths.add(path)
                size = get_path_size(path)
                targets.append(
                    CleanTarget(
                        path=path,
                        project_path=project_path,
                        size_bytes=size,
                        is_dir=is_dir,
                        target_type=subpath,
                        is_optional=is_opt,
                    )
                )

        # Look for *.egg-info in root
        try:
            for item in project_path.glob("*.egg-info"):
                if item not in seen_paths:
                    seen_paths.add(item)
                    size = get_path_size(item)
                    targets.append(
                        CleanTarget(
                            path=item,
                            project_path=project_path,
                            size_bytes=size,
                            is_dir=item.is_dir(),
                            target_type="*.egg-info",
                        )
                    )
        except Exception:
            pass

        # Find __pycache__ directories (limit depth to 4 to stay fast and avoid venvs)
        def _find_pycache(current_dir: Path, depth: int):
            if depth > 4:
                return
            try:
                with os.scandir(current_dir) as entries:
                    for entry in entries:
                        if entry.is_symlink():
                            continue
                        if entry.name in {".git", ".venv", "venv", "env", "node_modules", "build"}:
                            continue
                        if entry.is_dir():
                            dir_path = Path(entry.path)
                            if entry.name == "__pycache__":
                                if dir_path not in seen_paths:
                                    seen_paths.add(dir_path)
                                    size = get_path_size(dir_path)
                                    targets.append(
                                        CleanTarget(
                                            path=dir_path,
                                            project_path=project_path,
                                            size_bytes=size,
                                            is_dir=True,
                                            target_type="__pycache__",
                                        )
                                    )
                            else:
                                _find_pycache(dir_path, depth + 1)
            except (OSError, PermissionError):
                pass

        _find_pycache(project_path, 1)

        return targets
