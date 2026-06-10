"""
Clean command entry for the Seedling-tools.
Copyright (c) 2026 Kaelen Chow. All rights reserved.
"""

from __future__ import annotations
import argparse
from pathlib import Path
from typing import Final, List, Set, Tuple

from ...utils import (
    logger,
    terminal,
    get_package_version,
    io_processor,
    ConfigurationError,
    FileSystemError
)

__all__ = [
    "setup_clean_parser",
    "handle_clean"
]

IGNORED_DIR_NAMES: Final[Set[str]] = {
    ".git",
    ".venv",
    "venv",
    "env",
    ".env",
    "node_modules"
}

RECURSIVE_CACHE_DIR_NAMES: Final[Set[str]] = {
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    ".tox",
    ".nox"
}

RECURSIVE_CACHE_SUFFIXES: Final[Set[str]] = {
    ".pyc",
    ".pyo",
    ".pyd"
}

ROOT_BUILD_DIR_NAMES: Final[Tuple[str, ...]] = (
    "build",
    "dist"
)


def setup_clean_parser(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--version", action="version", version=f"Seedling-tools v{get_package_version()}")
    parser.add_argument("target", nargs="?", default=".", help="Target directory to clean")
    parser.add_argument("--dry-run", action="store_true", help="Preview deletions without executing")


def handle_clean(args: argparse.Namespace) -> None:
    terminal.configure_environment()
    logger.configure(verbose=False, quiet=False)

    try:
        target_path: Path = Path(args.target).resolve(strict=True)
    except (OSError, RuntimeError) as err:
        raise ConfigurationError(
            message=f"Target '{args.target}' does not exist.",
            hint="Please provide a valid directory to clean."
        ) from err

    if target_path.is_dir() is False:
        raise ConfigurationError(message=f"Target '{args.target}' is not a directory.")

    logger.info(f"Scanning Python cache artifacts in: {target_path.name}/")

    to_delete_dirs: List[Path]
    to_delete_files: List[Path]
    to_delete_dirs, to_delete_files = _collect_cleanup_targets(target_path)

    total_items: int = len(to_delete_dirs) + len(to_delete_files)
    if total_items == 0:
        logger.info("No caches found. Your project is already clean.")
        return

    if args.dry_run is True:
        logger.info(f"[DRY-RUN] Targeted {total_items} items for deletion:")
        for directory in to_delete_dirs:
            logger.warning(f"  [WILL REMOVE DIR ] {directory.relative_to(target_path)}")
        for file_path in to_delete_files:
            logger.warning(f"  [WILL REMOVE FILE] {file_path.relative_to(target_path)}")
        return

    deleted_count: int = 0
    for directory in to_delete_dirs:
        if io_processor.validate_path_security(directory, target_path) is False:
            logger.warning(f"Skipped unsafe directory candidate: {directory}")
            continue
        try:
            io_processor.delete_path(directory)
            deleted_count += 1
        except FileSystemError as err:
            logger.error(str(err))

    for file_path in to_delete_files:
        if io_processor.validate_path_security(file_path, target_path) is False:
            logger.warning(f"Skipped unsafe file candidate: {file_path}")
            continue
        try:
            io_processor.delete_path(file_path)
            deleted_count += 1
        except FileSystemError as err:
            logger.error(str(err))

    logger.info(f"Cleanup complete. {deleted_count} cache items removed.")


def _collect_cleanup_targets(target_path: Path) -> Tuple[List[Path], List[Path]]:
    to_delete_dirs: List[Path] = []
    to_delete_files: List[Path] = []
    shallow_cleanup_dirs: Set[Path] = set()

    for directory_name in ROOT_BUILD_DIR_NAMES:
        candidate: Path = target_path / directory_name
        if candidate.is_symlink() is True:
            continue
        if candidate.is_dir() is True:
            if io_processor.validate_path_security(candidate, target_path) is True:
                to_delete_dirs.append(candidate)
                shallow_cleanup_dirs.add(candidate)

    for egg_info in target_path.glob("*.egg-info"):
        if egg_info.is_symlink() is True:
            continue
        if egg_info.is_dir() is True:
            if io_processor.validate_path_security(egg_info, target_path) is True:
                to_delete_dirs.append(egg_info)
                shallow_cleanup_dirs.add(egg_info)

    directories_to_scan: List[Path] = [target_path]
    while len(directories_to_scan) > 0:
        current_dir: Path = directories_to_scan.pop()
        try:
            children: List[Path] = list(current_dir.iterdir())
        except OSError:
            continue

        for child in children:
            if child.is_symlink() is True:
                continue
            if child in shallow_cleanup_dirs:
                continue

            if child.is_dir() is True:
                if child.name in IGNORED_DIR_NAMES:
                    continue
                if child.name in RECURSIVE_CACHE_DIR_NAMES:
                    if io_processor.validate_path_security(child, target_path) is True:
                        to_delete_dirs.append(child)
                    continue
                directories_to_scan.append(child)
            elif child.is_file() is True:
                if child.suffix in RECURSIVE_CACHE_SUFFIXES:
                    if io_processor.validate_path_security(child, target_path) is True:
                        to_delete_files.append(child)
                elif child.name == ".coverage":
                    if io_processor.validate_path_security(child, target_path) is True:
                        to_delete_files.append(child)

    to_delete_dirs = sorted(to_delete_dirs, key=lambda item: str(item.relative_to(target_path)))
    to_delete_files = sorted(to_delete_files, key=lambda item: str(item.relative_to(target_path)))

    return to_delete_dirs, to_delete_files
