"""
Registry of project cleaners.
"""

from typing import Dict, List, Type
from .base import BaseCleaner
from .flutter import FlutterCleaner
from .node import NodeCleaner
from .python import PythonCleaner
from .gradle import GradleCleaner
from .xcode import XcodeCleaner
from .rust import RustCleaner

CLEANER_CLASSES: List[Type[BaseCleaner]] = [
    FlutterCleaner,
    NodeCleaner,
    PythonCleaner,
    GradleCleaner,
    XcodeCleaner,
    RustCleaner,
]


def get_all_cleaners() -> List[BaseCleaner]:
    """Return instances of all available cleaners."""
    return [cls() for cls in CLEANER_CLASSES]


def get_cleaners_dict() -> Dict[str, BaseCleaner]:
    """Return dictionary of cleaners mapped by key."""
    return {c.key: c for c in get_all_cleaners()}
