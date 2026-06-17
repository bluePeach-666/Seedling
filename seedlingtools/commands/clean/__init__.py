"""
Clean command entry for the Seedling-tools.
Copyright (c) 2026 Kaelen Chow. All rights reserved.
"""

from __future__ import annotations
import argparse
import json
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Final, List, Optional, Set, Tuple

from ...core import CleanConfig, config_manager
from ...utils import (
    logger,
    terminal,
    get_package_version,
    io_processor,
    CleanRiskError,
    ConfigurationError,
    FileSystemError
)

__all__ = [
    "setup_clean_parser",
    "handle_clean"
]

SAFE_STRATEGY_NAMES: Final[Tuple[str, ...]] = (
    "python-standard",
    "node-modules",
    "aggressive"
)

PROTECTED_DIR_NAMES: Final[Set[str]] = {
    "src",
    "seedlingtools",
    "tests"
}

SYSTEM_ROOT_NAMES: Final[Set[str]] = {
    "bin",
    "boot",
    "dev",
    "etc",
    "lib",
    "opt",
    "private",
    "sbin",
    "System",
    "tmp",
    "usr",
    "var",
    "Users"
}


@dataclass(frozen=True)
class CleanTarget:
    path: Path
    reason: str
    recursive: bool


class CleanRiskGuard:
    def validate(self, target_path: Path, candidate: CleanTarget) -> None:
        resolved_target: Path = target_path.resolve(strict=False)
        resolved_candidate: Path = candidate.path.resolve(strict=False)
        resolved_home: Path = Path.home().resolve(strict=False)

        if resolved_candidate == resolved_target:
            raise CleanRiskError(
                message=f"Refusing to delete the clean target root: {resolved_candidate}",
                context={"path": str(resolved_candidate)}
            )

        if resolved_candidate == resolved_home:
            raise CleanRiskError(
                message=f"Refusing to delete HOME directory: {resolved_candidate}",
                context={"path": str(resolved_candidate)}
            )

        if io_processor.validate_path_security(resolved_candidate, resolved_target) is False:
            raise CleanRiskError(
                message=f"Refusing to delete path outside clean target: {resolved_candidate}",
                context={"path": str(resolved_candidate), "target": str(resolved_target)}
            )

        if candidate.path.is_symlink() is True:
            raise CleanRiskError(
                message=f"Refusing to delete symlink candidate: {candidate.path}",
                context={"path": str(candidate.path)}
            )

        if resolved_candidate.parent == resolved_target:
            if resolved_candidate.name in PROTECTED_DIR_NAMES:
                raise CleanRiskError(
                    message=f"Refusing to delete protected source directory: {resolved_candidate.name}",
                    context={"path": str(resolved_candidate)}
                )

        if resolved_candidate == resolved_candidate.anchor and len(str(resolved_candidate)) <= 1:
            raise CleanRiskError(
                message=f"Refusing to delete filesystem root: {resolved_candidate}",
                context={"path": str(resolved_candidate)}
            )

        if resolved_candidate.parent == resolved_candidate.anchor:
            if resolved_candidate.name in SYSTEM_ROOT_NAMES:
                raise CleanRiskError(
                    message=f"Refusing to delete system directory: {resolved_candidate}",
                    context={"path": str(resolved_candidate)}
                )


class CleanStrategy:
    def collect(self, target_path: Path, config: CleanConfig) -> List[CleanTarget]:
        raise NotImplementedError


class PythonStandardStrategy(CleanStrategy):
    def collect(self, target_path: Path, config: CleanConfig) -> List[CleanTarget]:
        candidates: List[CleanTarget] = []
        shallow_cleanup_dirs: Set[Path] = set()
        ignore_names: Set[str] = set(config.ignore_dirs)
        recursive_dir_names: Set[str] = set(config.recursive_dirs)
        recursive_suffixes: Set[str] = set(config.extensions)

        for directory_name in config.root_only_dirs:
            candidate: Path = target_path / directory_name
            if candidate.is_symlink() is True:
                continue
            if candidate.is_dir() is True:
                candidates.append(CleanTarget(path=candidate, reason="root-build-dir", recursive=True))
                shallow_cleanup_dirs.add(candidate)

        for egg_info in target_path.glob("*.egg-info"):
            if egg_info.is_symlink() is True:
                continue
            if egg_info.is_dir() is True:
                candidates.append(CleanTarget(path=egg_info, reason="egg-info", recursive=True))
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
                    if child.name in ignore_names:
                        continue
                    if child.name in recursive_dir_names:
                        candidates.append(CleanTarget(path=child, reason="cache-dir", recursive=True))
                        continue
                    directories_to_scan.append(child)
                elif child.is_file() is True:
                    if child.suffix in recursive_suffixes:
                        candidates.append(CleanTarget(path=child, reason="compiled-artifact", recursive=False))
                    elif child.name == ".coverage":
                        candidates.append(CleanTarget(path=child, reason="coverage-file", recursive=False))

        candidates.extend(_collect_custom_targets(target_path, config))
        candidates.extend(_collect_external_script_targets(target_path, config))
        return _dedupe_clean_targets(candidates)


class NodeModulesStrategy(CleanStrategy):
    def collect(self, target_path: Path, config: CleanConfig) -> List[CleanTarget]:
        candidates: List[CleanTarget] = PythonStandardStrategy().collect(target_path, config)
        node_related_dirs: Tuple[str, ...] = (".next", ".nuxt", ".pnpm-store", ".yarn", ".parcel-cache")
        for directory_name in node_related_dirs:
            candidate: Path = target_path / directory_name
            if candidate.is_symlink() is True:
                continue
            if candidate.is_dir() is True:
                candidates.append(CleanTarget(path=candidate, reason="node-cache", recursive=True))
        return _dedupe_clean_targets(candidates)


class AggressiveStrategy(CleanStrategy):
    def collect(self, target_path: Path, config: CleanConfig) -> List[CleanTarget]:
        candidates: List[CleanTarget] = NodeModulesStrategy().collect(target_path, config)
        extra_root_dirs: Tuple[str, ...] = ("htmlcov", ".coverage_cache")
        for directory_name in extra_root_dirs:
            candidate: Path = target_path / directory_name
            if candidate.is_symlink() is True:
                continue
            if candidate.is_dir() is True:
                candidates.append(CleanTarget(path=candidate, reason="aggressive-cache", recursive=True))
        return _dedupe_clean_targets(candidates)


def setup_clean_parser(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--version", action="version", version=f"Seedling-tools v{get_package_version()}")
    parser.add_argument("target", nargs="?", default=".", help="Target directory to clean")
    parser.add_argument("--dry-run", action="store_true", default=None, help="Preview deletions without executing")
    parser.add_argument(
        "--strategy",
        choices=list(SAFE_STRATEGY_NAMES),
        default=None,
        help="Cleanup strategy to use"
    )


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

    config_manager.initialize(cwd=target_path, quiet_init=True)
    clean_config: CleanConfig = config_manager.build_clean_config(args)
    dry_run_flag: bool = clean_config.dry_run_default

    strategy: CleanStrategy = _resolve_clean_strategy(clean_config)

    logger.info(f"Scanning cleanup artifacts in: {target_path.name}/")
    logger.info(f"Using clean strategy: {clean_config.strategy}")

    to_delete: List[CleanTarget] = strategy.collect(target_path, clean_config)
    guarded_targets: List[CleanTarget] = _apply_risk_guard(target_path, to_delete)

    total_items: int = len(guarded_targets)
    if clean_config.strategy == "aggressive" and dry_run_flag is False:
        raise CleanRiskError(
            message="Aggressive clean strategy requires --dry-run or clean.dry_run_default=true before deletion.",
            context={"strategy": clean_config.strategy}
        )

    if total_items == 0:
        logger.info("No caches found. Your project is already clean.")
        return

    if dry_run_flag is True:
        logger.info(f"[DRY-RUN] Targeted {total_items} items for deletion:")
        for target in guarded_targets:
            marker: str = "DIR" if target.recursive is True else "FILE"
            logger.warning(f"  [WILL REMOVE {marker:<4}] {target.path.relative_to(target_path)} ({target.reason})")
        return

    deleted_count: int = 0
    for target in guarded_targets:
        try:
            io_processor.delete_path(target.path)
            deleted_count += 1
        except FileSystemError as err:
            logger.error(str(err))

    logger.info(f"Cleanup complete. {deleted_count} cache items removed.")


def _resolve_clean_strategy(config: CleanConfig) -> CleanStrategy:
    normalized: str = config.strategy.strip().lower()
    if normalized == "python-standard":
        return PythonStandardStrategy()
    if normalized == "node-modules":
        return NodeModulesStrategy()
    if normalized == "aggressive":
        return AggressiveStrategy()
    raise ConfigurationError(
        message=f"Unsupported clean strategy: {config.strategy}",
        hint="Use one of: python-standard, node-modules, aggressive."
    )


def _apply_risk_guard(target_path: Path, targets: List[CleanTarget]) -> List[CleanTarget]:
    guard: CleanRiskGuard = CleanRiskGuard()
    approved: List[CleanTarget] = []
    for target in targets:
        guard.validate(target_path, target)
        approved.append(target)
    return approved


def _dedupe_clean_targets(targets: List[CleanTarget]) -> List[CleanTarget]:
    deduped: Dict[Path, CleanTarget] = {}
    for target in targets:
        resolved_path: Path = target.path.resolve(strict=False)
        if resolved_path not in deduped:
            deduped[resolved_path] = target
    return sorted(deduped.values(), key=lambda item: str(item.path))


def _collect_custom_targets(target_path: Path, config: CleanConfig) -> List[CleanTarget]:
    candidates: List[CleanTarget] = []
    for raw_target in config.custom_targets:
        clean_target: str = raw_target.strip()
        if len(clean_target) == 0:
            continue
        if Path(clean_target).is_absolute() is True:
            candidate = Path(clean_target).resolve(strict=False)
        else:
            candidate = (target_path / clean_target).resolve(strict=False)
        if candidate.exists() is False:
            continue
        recursive: bool = candidate.is_dir()
        candidates.append(CleanTarget(path=candidate, reason="custom-target", recursive=recursive))
    return candidates


def _collect_external_script_targets(target_path: Path, config: CleanConfig) -> List[CleanTarget]:
    if config.external_script is None:
        return []

    if config.external_mode != "candidates-only":
        raise ConfigurationError(
            message=f"Unsupported clean.external_mode: {config.external_mode}",
            hint="Use 'candidates-only' for external clean scripts."
        )

    script_path: Path = config.external_script
    if script_path.is_absolute() is False:
        script_path = (target_path / script_path).resolve(strict=False)

    if script_path.exists() is False:
        raise ConfigurationError(
            message=f"External clean script does not exist: {script_path}",
            context={"path": str(script_path)}
        )

    command: List[str] = [
        sys.executable,
        str(script_path),
        "--target",
        str(target_path),
        "--strategy",
        config.strategy,
        "--dry-run",
        "true"
    ]

    try:
        process_result: subprocess.CompletedProcess[str] = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=True,
            cwd=str(target_path)
        )
    except subprocess.CalledProcessError as err:
        raise ConfigurationError(
            message=f"External clean script failed: {script_path}",
            hint="Ensure the script exits successfully and prints valid JSON.",
            context={"path": str(script_path), "stderr": err.stderr.strip()}
        ) from err
    except OSError as err:
        raise ConfigurationError(
            message=f"Failed to execute external clean script: {script_path}",
            context={"path": str(script_path)}
        ) from err

    try:
        payload: object = json.loads(process_result.stdout)
    except json.JSONDecodeError as err:
        raise ConfigurationError(
            message=f"External clean script returned invalid JSON: {script_path}",
            hint="Return a JSON object with a 'candidates' array.",
            context={"path": str(script_path)}
        ) from err

    if isinstance(payload, dict) is False:
        raise ConfigurationError(
            message=f"External clean script must return a JSON object: {script_path}",
            context={"path": str(script_path)}
        )

    raw_candidates: object = payload.get("candidates")
    if isinstance(raw_candidates, list) is False:
        raise ConfigurationError(
            message=f"External clean script must provide a 'candidates' list: {script_path}",
            context={"path": str(script_path)}
        )

    candidates: List[CleanTarget] = []
    for entry in raw_candidates:
        if isinstance(entry, str) is False:
            raise ConfigurationError(
                message=f"External clean candidate entries must be strings: {script_path}",
                context={"path": str(script_path)}
            )
        candidate_path: Path = (target_path / entry).resolve(strict=False)
        if candidate_path.exists() is False:
            continue
        candidates.append(
            CleanTarget(
                path=candidate_path,
                reason="external-script",
                recursive=candidate_path.is_dir()
            )
        )

    return candidates


def _collect_cleanup_targets(target_path: Path) -> Tuple[List[Path], List[Path]]:
    config: CleanConfig = CleanConfig()
    strategy: CleanStrategy = PythonStandardStrategy()
    collected: List[CleanTarget] = strategy.collect(target_path, config)

    directory_targets: List[Path] = []
    file_targets: List[Path] = []
    for target in collected:
        if target.recursive is True:
            directory_targets.append(target.path)
        else:
            file_targets.append(target.path)
    return directory_targets, file_targets
