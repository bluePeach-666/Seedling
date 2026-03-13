"""
🌲 Seedling
=============================================
A powerful 3-in-1 CLI toolkit to:
1. SCAN: Export directory structures to MD, TXT, or Images.
2. FIND: Perform exact and fuzzy searches with automated reports.
3. BUILD: Construct real file systems from text-based blueprints.

Author: Blue Peach
"""

from importlib.metadata import version, PackageNotFoundError

try:
    __version__ = version("Seedling-tools")
except PackageNotFoundError:
    __version__ = "dev"

__author__ = "Blue Peach"

from .core.filesystem import scan_dir_lines, search_items, get_full_context
from .commands.build.architect import build_structure_from_file

__all__ = [
    "scan_dir_lines",
    "search_items",
    "get_full_context",
    "build_structure_from_file",
    "__version__"
]