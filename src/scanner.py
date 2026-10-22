"""
Recursive project scanner with intelligent depth limits and ignore rules.
"""

import os
from pathlib import Path
from typing import Callable, List, Optional, Set

from .cleaners import get_all_cleaners
from .cleaners.base import BaseCleaner
from .config import DEFAULT_IGNORE_DIRS, DEFAULT_SCAN_DEPTH
from .models import Project
from .utils import get_last_modified


class ProjectScanner:
    """Scans directories to discover software projects and calculate cleanable disk space."""

    def __init__(
        self,
        cleaners: Optional[List[BaseCleaner]] = None,
        ignore_dirs: Optional[Set[str]] = None,
        max_depth: int = DEFAULT_SCAN_DEPTH,
        include_optional: bool = False,
    ):
        self.cleaners = cleaners if cleaners is not None else get_all_cleaners()
        self.ignore_dirs = set(DEFAULT_IGNORE_DIRS)
        if ignore_dirs:
            self.ignore_dirs.update(ignore_dirs)
        self.max_depth = max_depth
        self.include_optional = include_optional

    def scan(
        self,
        root_path: Path,
        progress_callback: Optional[Callable[[str], None]] = None,
    ) -> List[Project]:
        """
        Scan root_path recursively for projects up to max_depth.
        """
        root_path = root_path.resolve()
        discovered_projects: List[Project] = []
        visited_dirs: Set[str] = set()

        if not root_path.exists() or not root_path.is_dir():
            return discovered_projects

        # Check if root_path itself is a project
        self._check_and_add_project(root_path, discovered_projects, progress_callback)

        def _walk(current_path: Path, current_depth: int):
            if current_depth > self.max_depth:
                return

            try:
                with os.scandir(current_path) as entries:
                    for entry in entries:
                        try:
                            if entry.is_symlink():
                                continue

                            if not entry.is_dir():
                                continue

                            entry_name = entry.name
                            if entry_name in self.ignore_dirs or entry_name.startswith("."):
                                # If it's a hidden folder other than root, skip traversing into it
                                continue

                            dir_path = Path(entry.path)
                            dir_real_str = str(dir_path.resolve())
                            if dir_real_str in visited_dirs:
                                continue
                            visited_dirs.add(dir_real_str)

                            if progress_callback:
                                progress_callback(str(dir_path))

                            # Check if this directory is a project
                            is_project = self._check_and_add_project(
                                dir_path, discovered_projects, progress_callback
                            )

                            # If it is a project (e.g. flutter / node), we generally don't need to dive
                            # deeply into its internal source folders looking for subprojects, EXCEPT
                            # mono-repos (like 'packages/' or 'apps/').
                            # We can walk one level deeper if it has packages/ or apps/ or client/server.
                            if is_project:
                                # Look for subprojects like android/, ios/, frontend/, backend/, packages/
                                sub_check_names = {"packages", "apps", "client", "server", "frontend", "backend"}
                                for sub_name in sub_check_names:
                                    sub_folder = dir_path / sub_name
                                    if sub_folder.is_dir():
                                        _walk(sub_folder, current_depth + 1)
                            else:
                                _walk(dir_path, current_depth + 1)

                        except (OSError, PermissionError):
                            continue
            except (OSError, PermissionError):
                pass

        _walk(root_path, 1)

        # Sort projects by total cleanable size descending
        discovered_projects.sort(key=lambda p: p.total_cleanable_bytes, reverse=True)
        return discovered_projects

    def scan_multiple(
        self,
        root_paths: List[Path],
        progress_callback: Optional[Callable[[str], None]] = None,
    ) -> List[Project]:
        """Scan multiple root paths (e.g. Drive C: and Drive D:) and return combined projects."""
        combined_projects: List[Project] = []
        seen_paths: Set[str] = set()

        for rp in root_paths:
            projs = self.scan(rp, progress_callback=progress_callback)
            for p in projs:
                p_str = str(p.path.resolve())
                if p_str not in seen_paths:
                    seen_paths.add(p_str)
                    combined_projects.append(p)

        combined_projects.sort(key=lambda p: p.total_cleanable_bytes, reverse=True)
        return combined_projects

    def _check_and_add_project(
        self,
        dir_path: Path,
        project_list: List[Project],
        progress_callback: Optional[Callable[[str], None]] = None,
    ) -> bool:
        """Inspect directory with all cleaners. If it matches, add to project_list."""
        matched_any = False

        for cleaner in self.cleaners:
            try:
                if cleaner.detect(dir_path):
                    matched_any = True
                    targets = cleaner.find_targets(dir_path, include_optional=self.include_optional)
                    # We record project even if 0 targets, but total size is 0
                    last_mod = get_last_modified(dir_path)
                    
                    project = Project(
                        path=dir_path,
                        name=dir_path.name,
                        project_type=cleaner.key,
                        display_name=cleaner.display_name,
                        targets=targets,
                        last_modified=last_mod,
                        has_clean_command=(cleaner.key in {"flutter", "rust"}),
                    )
                    project_list.append(project)
                    # Once a cleaner matches this specific directory (e.g. Flutter), we don't
                    # also treat it as standalone gradle unless configured.
                    break
            except Exception:
                continue

        return matched_any
