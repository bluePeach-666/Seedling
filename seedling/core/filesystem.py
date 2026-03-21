"""
Filesystem traversal and tree generation module.

This module provides the core scanning and search functionality for Seedling.
For better code organization, some components have been moved to specialized modules:
- ScanConfig, constants -> config.py
- is_text_file, is_binary_content -> detection.py
- matches_*_pattern, is_valid_item -> patterns.py
- traverse_directory, TraversalResult -> traversal.py

All symbols remain importable from this module for backward compatibility.
"""
import sys
import difflib
from pathlib import Path
from typing import Set, List, Optional, Dict, Tuple

# Re-export from specialized modules for backward compatibility
from .config import (
    ScanConfig, MAX_FILE_SIZE, MAX_ITERATION_DEPTH,
    HARD_DEPTH_LIMIT, SPECIAL_TEXT_NAMES, TEXT_EXTENSIONS, FILE_TYPE_MAP
)
from .detection import is_text_file, is_binary_content
from .patterns import matches_exclude_pattern, matches_include_pattern, is_valid_item
from .traversal import traverse_directory, TraversalResult, TraversalItem

from .ui import print_progress_bar
from .logger import logger
from .sysinfo import get_system_mem_limit_mb


def safe_read_text(file_path: Path, quiet: bool = False) -> Optional[str]:
    """Try multiple encodings to read text content."""
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


def scan_dir_lines(dir_path: Path, config: ScanConfig, stats: Dict[str, int]) -> List[str]:
    """Generate directory tree lines using DFS traversal."""
    lines = []
    path = Path(dir_path)
    base_dir = path.resolve()
    seen_real_paths = {base_dir}

    def _get_children(p: Path) -> List[Path]:
        valid_items = [
            item for item in p.iterdir()
            if is_valid_item(item, base_dir, config)
        ]
        valid_items.sort(key=lambda x: (not x.is_dir(), x.name.lower()))
        return valid_items

    # Capture root directory permission errors
    try:
        initial_items = _get_children(path)
    except PermissionError:
        lines.append("[Permission Denied - Cannot read directory]")
        return lines

    stack: List[Tuple[Path, int, str, bool]] = []
    for i, item in enumerate(reversed(initial_items)):
        stack.append((item, 1, "", i == 0))

    while stack:
        item, depth, curr_prefix, is_last = stack.pop()
        if depth > HARD_DEPTH_LIMIT:
            if not config.quiet:
                lines.append(f"{curr_prefix}└── ⚠️ [SYSTEM MAX DEPTH REACHED]")
            continue

        connector = "└── " if is_last else "├── "
        symlink_mark = " (symlink)" if item.is_symlink() else ""
        match_mark = " 🎯 [MATCHED]" if item in config.highlights else ""
        display_name = f"{item.name}/" if item.is_dir() else item.name
        lines.append(f"{curr_prefix}{connector}{display_name}{symlink_mark}{match_mark}")

        if item.is_dir():
            stats["dirs"] += 1
        else:
            stats["files"] += 1

        total_scanned = stats["dirs"] + stats["files"]
        if total_scanned % 15 == 0:
            print_progress_bar(total_scanned, label="Scanning", quiet=config.quiet)

        # Descend into subdirectories
        if item.is_dir() and not item.is_symlink():
            if config.max_depth is not None and depth >= config.max_depth:
                continue

            try:
                real_path = item.resolve(strict=True)
                if real_path in seen_real_paths:
                    if not config.quiet:
                        lines.append(f"{curr_prefix}    └── 🔄 [Recursion Blocked]")
                    continue
                seen_real_paths.add(real_path)
            except Exception:
                pass

            # Capture subdirectory permission errors
            try:
                children = _get_children(item)
            except PermissionError:
                extension = "    " if is_last else "│   "
                lines.append(f"{curr_prefix}{extension}[Permission Denied - Cannot read directory]")
                continue

            new_prefix = curr_prefix + ("    " if is_last else "│   ")
            for i, child in enumerate(reversed(children)):
                stack.append((child, depth + 1, new_prefix, i == 0))

    return lines


def search_items(dir_path: Path, keyword: str, config: ScanConfig) -> Tuple[List[Path], List[Path]]:
    """Search for files and folders, supporting regular expressions."""
    import re
    exact_matches: List[Path] = []
    all_seen: List[Tuple[str, Path]] = []
    base_dir = dir_path.resolve()
    count = 0

    # Compile regex if enabled
    regex_pattern = None
    if config.use_regex:
        try:
            regex_pattern = re.compile(keyword, re.IGNORECASE)
        except re.error as e:
            logger.error(f"Invalid regex pattern: {e}")
            return [], []
        keyword_lower = None
    else:
        keyword_lower = keyword.lower()

    stack = [dir_path]
    while stack:
        curr = stack.pop()
        try:
            for item in curr.iterdir():
                if not is_valid_item(item, base_dir, config):
                    continue

                count += 1
                all_seen.append((item.name, item))

                # Match using regex or substring
                if config.use_regex and regex_pattern:
                    if regex_pattern.search(item.name):
                        exact_matches.append(item)
                else:
                    if keyword_lower in item.name.lower():
                        exact_matches.append(item)

                if count % 15 == 0:
                    print_progress_bar(count, label="Searching", icon="🔍", quiet=config.quiet)

                if item.is_dir() and not item.is_symlink():
                    stack.append(item)
        except PermissionError:
            pass

    # Fuzzy matching logic (skip for regex mode)
    fuzzy_matches = []
    if not config.use_regex:
        unique_names = list(set([n for n, p in all_seen]))
        close_names = difflib.get_close_matches(keyword, unique_names, n=10, cutoff=0.7)
        fuzzy_matches = [p for n, p in all_seen if n in close_names and p not in exact_matches]

    return exact_matches, fuzzy_matches


def get_full_context(target_path: Path, config: ScanConfig) -> List[Tuple[Path, str]]:
    """Collect content of all text files (Power Mode)."""
    context_data = []
    dynamic_limit_mb = get_system_mem_limit_mb()
    # Use 80% of system limit for safety margin
    total_mem_limit = int(dynamic_limit_mb * 1024 * 1024 * 0.8)
    curr_mem_usage = 0
    base_dir = target_path.resolve()

    stack = [(target_path, 0)]
    while stack:
        curr, depth = stack.pop()
        if config.max_depth and depth >= config.max_depth:
            continue

        try:
            items = sorted(list(curr.iterdir()), key=lambda x: (not x.is_dir(), x.name.lower()))
            for item in items:
                if not is_valid_item(item, base_dir, config):
                    continue

                if item.is_file():
                    try:
                        f_stat = item.stat()
                        if f_stat.st_size > MAX_FILE_SIZE:
                            continue

                        content = safe_read_text(item, quiet=config.quiet)
                        if content is not None:
                            # Use sys.getsizeof for accurate memory measurement
                            actual_size = sys.getsizeof(content)

                            if actual_size > MAX_FILE_SIZE * 2:
                                logger.debug(f"Memory limit triggered (decoded) for {item.name}")
                                continue

                            if curr_mem_usage + actual_size > total_mem_limit:
                                logger.error(f"Hardware RAM limit ({dynamic_limit_mb}MB) reached! Safety abort.")
                                logger.info(f"Processed {len(context_data)} files before limit.")
                                return context_data

                            context_data.append((item.relative_to(base_dir), content))
                            curr_mem_usage += actual_size
                    except Exception:
                        pass
                elif item.is_dir() and not item.is_symlink():
                    stack.append((item, depth + 1))
        except PermissionError:
            pass

    return context_data
