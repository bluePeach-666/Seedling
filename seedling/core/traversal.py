"""
Unified traversal engine with caching for Seedling.
Provides single-pass directory traversal to avoid redundant I/O.
"""
import sys
from pathlib import Path
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple

from .config import ScanConfig, MAX_FILE_SIZE, HARD_DEPTH_LIMIT
from .detection import is_text_file, is_binary_content
from .patterns import is_valid_item
from .ui import print_progress_bar
from .logger import logger
from .sysinfo import get_system_mem_limit_mb


@dataclass
class TraversalItem:
    """Represents a single item discovered during traversal."""
    path: Path
    relative_path: Path
    is_dir: bool
    is_symlink: bool
    depth: int


@dataclass
class TraversalResult:
    """Complete result of a single traversal pass with caching."""
    items: List[TraversalItem] = field(default_factory=list)
    text_files: List[TraversalItem] = field(default_factory=list)
    directories: List[TraversalItem] = field(default_factory=list)
    stats: Dict[str, int] = field(default_factory=lambda: {"dirs": 0, "files": 0})

    # Content cache - stores file contents to avoid re-reading
    _content_cache: Dict[Path, Optional[str]] = field(default_factory=dict)
    _mem_usage: int = field(default=0, repr=False)
    _mem_limit: int = field(default=0, repr=False)

    def get_content(self, item: TraversalItem, quiet: bool = False) -> Optional[str]:
        """
        Get file content with caching - reads each file only once.
        Returns None for directories or binary files.
        """
        if item.is_dir:
            return None

        if item.path not in self._content_cache:
            self._content_cache[item.path] = _safe_read_text_cached(
                item.path, quiet=quiet
            )
        return self._content_cache[item.path]

    def can_add_content(self, estimated_size: int) -> bool:
        """Check if we can add more content within memory limits."""
        if self._mem_limit == 0:
            return True
        return self._mem_usage + estimated_size <= self._mem_limit

    def add_to_cache(self, path: Path, content: Optional[str], size: int):
        """Add content to cache with memory tracking."""
        self._content_cache[path] = content
        if content:
            self._mem_usage += size


def _safe_read_text_cached(file_path: Path, quiet: bool = False) -> Optional[str]:
    """Multi-encoding text reader for caching."""
    if is_binary_content(file_path):
        return None

    encodings = ['utf-8', 'gbk', 'big5', 'utf-16', 'latin-1']
    for enc in encodings:
        try:
            with open(file_path, 'r', encoding=enc, errors='strict') as f:
                return f.read()
        except (UnicodeDecodeError, LookupError):
            continue

    if not quiet:
        logger.warning(f"Skipped {file_path.name}: Unsupported encoding.")
    return None


def traverse_directory(
    dir_path: Path,
    config: ScanConfig,
    collect_content: bool = False,
    content_limit_mb: Optional[int] = None
) -> TraversalResult:
    """
    Single-pass DFS traversal that collects everything needed.

    Args:
        dir_path: Target directory to traverse
        config: Scan configuration
        collect_content: If True, eagerly load all text file contents
        content_limit_mb: Memory limit for content collection (auto-calculated if None)

    Returns:
        TraversalResult with all discovered items and optional content cache
    """
    result = TraversalResult()

    # Set up memory limit for content collection
    if collect_content:
        limit_mb = content_limit_mb or get_system_mem_limit_mb()
        result._mem_limit = int(limit_mb * 1024 * 1024 * 0.8)  # 80% safety margin

    base_dir = dir_path.resolve()
    seen_real_paths = {base_dir}

    # Start with resolved directory path
    resolved_start = dir_path.resolve()
    stack: List[Tuple[Path, int]] = [(resolved_start, 0)]

    while stack:
        curr, depth = stack.pop()

        # Depth limit check
        if config.max_depth is not None and depth > config.max_depth:
            continue

        if depth > HARD_DEPTH_LIMIT:
            logger.warning(f"System max depth reached at {curr}")
            continue

        try:
            # Sort items: directories first, then alphabetically
            items = sorted(
                list(curr.iterdir()),
                key=lambda x: (not x.is_dir(), x.name.lower())
            )

            for item in items:
                if not is_valid_item(item, base_dir, config):
                    continue

                # Calculate item depth (children are at depth + 1)
                item_depth = depth + 1

                # Create traversal item
                rel_path = item.relative_to(base_dir)
                trav_item = TraversalItem(
                    path=item,
                    relative_path=rel_path,
                    is_dir=item.is_dir(),
                    is_symlink=item.is_symlink(),
                    depth=item_depth
                )

                result.items.append(trav_item)

                if item.is_dir():
                    result.stats["dirs"] += 1
                    result.directories.append(trav_item)
                else:
                    result.stats["files"] += 1

                    # Track text files
                    if is_text_file(item):
                        result.text_files.append(trav_item)

                        # Collect content if requested
                        if collect_content:
                            try:
                                f_stat = item.stat()
                                if f_stat.st_size <= MAX_FILE_SIZE:
                                    # Check memory before reading
                                    estimated = f_stat.st_size * 2  # Rough estimate for decoded
                                    if result.can_add_content(estimated):
                                        content = _safe_read_text_cached(item, quiet=config.quiet)
                                        if content:
                                            actual_size = sys.getsizeof(content)
                                            if result.can_add_content(actual_size):
                                                result.add_to_cache(item, content, actual_size)
                            except Exception:
                                pass

                # Progress reporting
                total = result.stats["dirs"] + result.stats["files"]
                if total % 15 == 0:
                    print_progress_bar(total, label="Scanning", quiet=config.quiet)

                # Add directories to stack for further traversal
                if item.is_dir() and not item.is_symlink():
                    # Check depth limit before adding to stack
                    if config.max_depth is not None and item_depth >= config.max_depth:
                        continue

                    try:
                        real_path = item.resolve(strict=True)
                        if real_path in seen_real_paths:
                            continue  # Avoid infinite recursion
                        seen_real_paths.add(real_path)
                    except Exception:
                        pass

                    stack.append((item, item_depth))

        except PermissionError:
            pass

    return result


def build_tree_lines(result: TraversalResult, config: ScanConfig, root_path: Optional[Path] = None) -> List[str]:
    """
    Build tree lines from a TraversalResult.
    This avoids re-traversing the filesystem.

    Args:
        result: TraversalResult from traverse_directory()
        config: ScanConfig with highlights set
        root_path: Optional root path to determine top-level items
    """
    lines = []

    if not result.items:
        return lines

    # Determine the root path from the first item
    if root_path is None and result.items:
        # Find the shallowest depth items and get their common parent
        min_depth = min(item.depth for item in result.items)
        root_level_items = [item for item in result.items if item.depth == min_depth]
        if root_level_items:
            # The root is the parent of top-level items
            root_path = root_level_items[0].path.parent

    # Group items by parent for hierarchical output
    items_by_parent: Dict[Path, List[TraversalItem]] = {}

    for item in result.items:
        parent = item.path.parent
        if parent not in items_by_parent:
            items_by_parent[parent] = []
        items_by_parent[parent].append(item)

    # Build tree recursively
    def _build_subtree(items: List[TraversalItem], prefix: str = ""):
        items.sort(key=lambda x: (not x.is_dir, x.path.name.lower()))

        for i, item in enumerate(items):
            is_last = (i == len(items) - 1)
            connector = "└── " if is_last else "├── "
            symlink_mark = " (symlink)" if item.is_symlink else ""
            match_mark = " 🎯 [MATCHED]" if item.path in config.highlights else ""
            display_name = f"{item.path.name}/" if item.is_dir else item.path.name

            lines.append(f"{prefix}{connector}{display_name}{symlink_mark}{match_mark}")

            # Find children
            if item.is_dir:
                children = items_by_parent.get(item.path, [])
                if children:
                    new_prefix = prefix + ("    " if is_last else "│   ")
                    _build_subtree(children, new_prefix)

    # Start with root-level items (direct children of root_path)
    if root_path and root_path in items_by_parent:
        root_items = items_by_parent[root_path]
        _build_subtree(root_items)

    return lines
