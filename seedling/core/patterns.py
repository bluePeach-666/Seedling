"""
Path pattern matching utilities for Seedling.
"""
import fnmatch
from pathlib import Path
from typing import List

from .config import ScanConfig, FILE_TYPE_MAP
from .detection import is_text_file


def matches_exclude_pattern(item_path: Path, base_dir: Path, exclude_patterns: List[str]) -> bool:
    """
    Check if path matches Git-style exclusion rules.
    """
    # Generate standard POSIX relative path starting with /
    rel_path = "/" + item_path.relative_to(base_dir).as_posix()
    item_name = item_path.name

    for pattern in exclude_patterns:
        is_dir_only = pattern.endswith('/')
        clean_pattern = pattern.rstrip('/')

        # Path-anchored rule
        if clean_pattern.startswith('/'):
            if fnmatch.fnmatch(rel_path, clean_pattern):
                if not is_dir_only or item_path.is_dir():
                    return True

        # Global rule
        else:
            # Match filename
            if fnmatch.fnmatch(item_name, clean_pattern):
                if not is_dir_only or item_path.is_dir():
                    return True
            # Match path segment
            if fnmatch.fnmatch(rel_path, f"*/{clean_pattern}") or \
               fnmatch.fnmatch(rel_path, f"*/{clean_pattern}/*") or \
               fnmatch.fnmatch(rel_path, f"**/{clean_pattern}"):
                if not is_dir_only or item_path.is_dir():
                    return True
    return False


def matches_include_pattern(item_path: Path, base_dir: Path, include_patterns: List[str]) -> bool:
    """
    Check if path matches Include filter rules.
    Supports glob patterns like **/*.py, *.md, src/**
    """
    if not include_patterns:
        return True

    rel_path = item_path.relative_to(base_dir)
    item_name = item_path.name

    for pattern in include_patterns:
        # Normalize pattern
        clean = pattern.lstrip('/')

        # Match file name directly (e.g., "*.py")
        if fnmatch.fnmatch(item_name, clean):
            return True

        # Use pathlib's match for glob patterns (supports **/*.py)
        try:
            if rel_path.match(pattern) or rel_path.match(clean):
                return True
            # Also try matching as if pattern is relative
            if pattern.startswith('**/'):
                if rel_path.match(pattern[3:]):
                    return True
        except (ValueError, TypeError):
            pass

        # Match path segment (e.g., "*/{pattern}" or "**/{pattern}")
        rel_str = rel_path.as_posix()
        if fnmatch.fnmatch(rel_str, clean) or fnmatch.fnmatch(rel_str, f"*/{clean}"):
            return True

    return False


def is_valid_item(item: Path, base_dir: Path, config: ScanConfig) -> bool:
    """Comprehensive validation for files/directories to include in results."""
    if not config.show_hidden and item.name.startswith('.'):
        return False

    if matches_exclude_pattern(item, base_dir, config.excludes):
        return False

    # Include filter - must match at least one pattern if specified
    # NOTE: Directories are always allowed through for traversal purposes
    # The actual filtering of results happens at output time
    if config.includes and item.is_file():
        if not matches_include_pattern(item, base_dir, config.includes):
            return False

    # File type filter
    if config.file_type and item.is_file():
        allowed = FILE_TYPE_MAP.get(config.file_type.lower())
        if allowed and item.suffix.lower() not in allowed:
            return False

    if config.text_only and item.is_file() and not is_text_file(item):
        return False
    return True
