"""
Cleaner for Node.js, JavaScript, and TypeScript web projects.
"""

from pathlib import Path
from typing import List

from ..models import CleanTarget
from ..utils import get_path_size
from .base import BaseCleaner


class NodeCleaner(BaseCleaner):
    @property
    def key(self) -> str:
        return "node"

    @property
    def display_name(self) -> str:
        return "Node.js / Web"

    def detect(self, project_path: Path) -> bool:
        package_json = project_path / "package.json"
        return package_json.is_file()

    def find_targets(self, project_path: Path, include_optional: bool = False) -> List[CleanTarget]:
        targets: List[CleanTarget] = []

        target_subpaths = [
            ("node_modules", True),
            (".next", True),
            (".nuxt", True),
            ("dist", True),
            (".output", True),
            ("build", True),
            (".turbo", True),
            (".cache", True),
            (".parcel-cache", True),
            (".svelte-kit", True),
            (".astro", True),
            ("coverage", True),
            (".docusaurus", True),
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
