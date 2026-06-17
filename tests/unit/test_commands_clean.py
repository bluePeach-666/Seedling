# Unit tests for Seedling-tools v2.5.
# Copyright (c) 2026 Kaelen Chow. All rights reserved.

from __future__ import annotations
import argparse
import json
from pathlib import Path
from typing import List

import pytest #type: ignore

from seedlingtools.commands.clean import handle_clean
from seedlingtools.commands.clean import _collect_cleanup_targets
from seedlingtools.utils import CleanRiskError, ConfigurationError


def _create_cache_project(tmp_path: Path) -> Path:
    project_path: Path = tmp_path / "project"
    project_path.mkdir()

    src_path: Path = project_path / "src"
    src_path.mkdir()
    main_file: Path = src_path / "main.py"
    main_file.write_text("print('hello')\n", encoding="utf-8")

    pycache_path: Path = src_path / "__pycache__"
    pycache_path.mkdir()
    compiled_file: Path = pycache_path / "main.cpython-312.pyc"
    compiled_file.write_bytes(b"cache")

    root_build_path: Path = project_path / "build"
    root_build_path.mkdir()
    build_file: Path = root_build_path / "artifact.txt"
    build_file.write_text("artifact\n", encoding="utf-8")

    nested_build_path: Path = src_path / "build"
    nested_build_path.mkdir()
    nested_build_file: Path = nested_build_path / "keep.txt"
    nested_build_file.write_text("keep\n", encoding="utf-8")

    pytest_cache_path: Path = project_path / ".pytest_cache"
    pytest_cache_path.mkdir()
    pytest_cache_file: Path = pytest_cache_path / "README.md"
    pytest_cache_file.write_text("cache\n", encoding="utf-8")

    egg_info_path: Path = project_path / "sample.egg-info"
    egg_info_path.mkdir()
    egg_info_file: Path = egg_info_path / "PKG-INFO"
    egg_info_file.write_text("metadata\n", encoding="utf-8")

    coverage_file: Path = project_path / ".coverage"
    coverage_file.write_text("coverage\n", encoding="utf-8")

    loose_pyc_file: Path = src_path / "loose.pyc"
    loose_pyc_file.write_bytes(b"loose")

    node_modules_path: Path = project_path / "node_modules" / "pkg" / "__pycache__"
    node_modules_path.mkdir(parents=True)
    node_cache_file: Path = node_modules_path / "ignored.pyc"
    node_cache_file.write_bytes(b"ignored")

    next_cache_path: Path = project_path / ".next"
    next_cache_path.mkdir()
    next_file: Path = next_cache_path / "cache.txt"
    next_file.write_text("node\n", encoding="utf-8")

    return project_path


def _write_clean_config(home_path: Path, payload: dict) -> None:
    config_dir: Path = home_path / ".seedling"
    config_dir.mkdir(parents=True, exist_ok=True)
    config_file: Path = config_dir / "config.json"
    config_file.write_text(json.dumps(payload), encoding="utf-8")


def test_collect_cleanup_targets_keeps_nested_build_directory(tmp_path: Path) -> None:
    project_path: Path = _create_cache_project(tmp_path)

    dirs: List[Path]
    files: List[Path]
    dirs, files = _collect_cleanup_targets(project_path)

    relative_dirs: List[Path] = []
    for directory in dirs:
        relative_dirs.append(directory.relative_to(project_path))

    relative_files: List[Path] = []
    for file_path in files:
        relative_files.append(file_path.relative_to(project_path))

    assert Path("build") in relative_dirs
    assert Path("src/__pycache__") in relative_dirs
    assert Path(".pytest_cache") in relative_dirs
    assert Path("sample.egg-info") in relative_dirs
    assert Path("src/build") not in relative_dirs
    assert Path("node_modules/pkg/__pycache__") not in relative_dirs
    assert Path("src/loose.pyc") in relative_files
    assert Path(".coverage") in relative_files


def test_handle_clean_dry_run_preserves_targets(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    home_path: Path = tmp_path / "home"
    home_path.mkdir()
    monkeypatch.setenv("HOME", str(home_path))
    monkeypatch.setenv("USERPROFILE", str(home_path))
    project_path: Path = _create_cache_project(tmp_path)
    args: argparse.Namespace = argparse.Namespace(target=str(project_path), dry_run=True, strategy=None)

    handle_clean(args)

    assert (project_path / "build").exists() is True
    assert (project_path / "src" / "__pycache__").exists() is True
    assert (project_path / ".coverage").exists() is True
    assert (project_path / "src" / "main.py").exists() is True


def test_handle_clean_removes_only_generated_artifacts(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    home_path: Path = tmp_path / "home"
    home_path.mkdir()
    monkeypatch.setenv("HOME", str(home_path))
    monkeypatch.setenv("USERPROFILE", str(home_path))
    project_path: Path = _create_cache_project(tmp_path)
    args: argparse.Namespace = argparse.Namespace(target=str(project_path), dry_run=None, strategy=None)

    handle_clean(args)

    assert (project_path / "build").exists() is False
    assert (project_path / "src" / "__pycache__").exists() is False
    assert (project_path / ".pytest_cache").exists() is False
    assert (project_path / "sample.egg-info").exists() is False
    assert (project_path / ".coverage").exists() is False
    assert (project_path / "src" / "loose.pyc").exists() is False

    assert (project_path / "src" / "main.py").exists() is True
    assert (project_path / "src" / "build" / "keep.txt").exists() is True
    assert (project_path / "node_modules" / "pkg" / "__pycache__" / "ignored.pyc").exists() is True


def test_handle_clean_noop_succeeds(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    home_path: Path = tmp_path / "home"
    home_path.mkdir()
    monkeypatch.setenv("HOME", str(home_path))
    monkeypatch.setenv("USERPROFILE", str(home_path))
    project_path: Path = tmp_path / "project"
    project_path.mkdir()
    source_file: Path = project_path / "main.py"
    source_file.write_text("print('clean')\n", encoding="utf-8")
    args: argparse.Namespace = argparse.Namespace(target=str(project_path), dry_run=None, strategy=None)

    handle_clean(args)

    assert source_file.exists() is True


def test_collect_cleanup_targets_ignores_symlinked_cache(tmp_path: Path) -> None:
    project_path: Path = tmp_path / "project"
    outside_path: Path = tmp_path / "outside"
    project_path.mkdir()
    outside_path.mkdir()
    outside_cache: Path = outside_path / "__pycache__"
    outside_cache.mkdir()
    outside_file: Path = outside_cache / "outside.pyc"
    outside_file.write_bytes(b"outside")

    symlink_path: Path = project_path / "linked_cache"
    try:
        symlink_path.symlink_to(outside_cache, target_is_directory=True)
    except OSError:
        return

    dirs: List[Path]
    files: List[Path]
    dirs, files = _collect_cleanup_targets(project_path)

    assert len(dirs) == 0
    assert len(files) == 0
    assert outside_file.exists() is True


def test_handle_clean_aggressive_requires_dry_run(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    home_path: Path = tmp_path / "home"
    home_path.mkdir()
    monkeypatch.setenv("HOME", str(home_path))
    monkeypatch.setenv("USERPROFILE", str(home_path))
    _write_clean_config(home_path, {"schema_version": 1, "clean": {"strategy": "aggressive"}, "state": {}})
    project_path: Path = _create_cache_project(tmp_path)
    args: argparse.Namespace = argparse.Namespace(target=str(project_path), dry_run=None, strategy=None)

    from seedlingtools.core.config_manager import SeedlingConfigManager
    from seedlingtools.utils.patterns import SingletonMeta
    if SeedlingConfigManager in SingletonMeta._instances:
        del SingletonMeta._instances[SeedlingConfigManager]

    with pytest.raises(CleanRiskError):
        handle_clean(args)


def test_handle_clean_node_modules_strategy_removes_node_cache(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    home_path: Path = tmp_path / "home"
    home_path.mkdir()
    monkeypatch.setenv("HOME", str(home_path))
    monkeypatch.setenv("USERPROFILE", str(home_path))
    _write_clean_config(home_path, {"schema_version": 1, "clean": {"strategy": "node-modules"}, "state": {}})
    project_path: Path = _create_cache_project(tmp_path)
    args: argparse.Namespace = argparse.Namespace(target=str(project_path), dry_run=None, strategy=None)

    from seedlingtools.core.config_manager import SeedlingConfigManager
    from seedlingtools.utils.patterns import SingletonMeta
    if SeedlingConfigManager in SingletonMeta._instances:
        del SingletonMeta._instances[SeedlingConfigManager]

    handle_clean(args)

    assert (project_path / ".next").exists() is False


def test_handle_clean_blocks_custom_target_outside_project(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    home_path: Path = tmp_path / "home"
    home_path.mkdir()
    monkeypatch.setenv("HOME", str(home_path))
    monkeypatch.setenv("USERPROFILE", str(home_path))
    outside_path: Path = tmp_path / "outside"
    outside_path.mkdir()
    outside_file: Path = outside_path / "outside.pyc"
    outside_file.write_bytes(b"outside")
    _write_clean_config(
        home_path,
        {"schema_version": 1, "clean": {"custom_targets": [str(outside_file)]}, "state": {}}
    )
    project_path: Path = _create_cache_project(tmp_path)
    args: argparse.Namespace = argparse.Namespace(target=str(project_path), dry_run=True, strategy=None)

    from seedlingtools.core.config_manager import SeedlingConfigManager
    from seedlingtools.utils.patterns import SingletonMeta
    if SeedlingConfigManager in SingletonMeta._instances:
        del SingletonMeta._instances[SeedlingConfigManager]

    with pytest.raises(CleanRiskError):
        handle_clean(args)


def test_handle_clean_blocks_protected_source_directory(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    home_path: Path = tmp_path / "home"
    home_path.mkdir()
    monkeypatch.setenv("HOME", str(home_path))
    monkeypatch.setenv("USERPROFILE", str(home_path))
    _write_clean_config(
        home_path,
        {"schema_version": 1, "clean": {"custom_targets": ["src"]}, "state": {}}
    )
    project_path: Path = _create_cache_project(tmp_path)
    args: argparse.Namespace = argparse.Namespace(target=str(project_path), dry_run=True, strategy=None)

    from seedlingtools.core.config_manager import SeedlingConfigManager
    from seedlingtools.utils.patterns import SingletonMeta
    if SeedlingConfigManager in SingletonMeta._instances:
        del SingletonMeta._instances[SeedlingConfigManager]

    with pytest.raises(CleanRiskError):
        handle_clean(args)


def test_handle_clean_external_mode_must_be_candidates_only(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    home_path: Path = tmp_path / "home"
    home_path.mkdir()
    monkeypatch.setenv("HOME", str(home_path))
    monkeypatch.setenv("USERPROFILE", str(home_path))
    script_path: Path = tmp_path / "script.py"
    script_path.write_text("print('{}')\n", encoding="utf-8")
    _write_clean_config(
        home_path,
        {
            "schema_version": 1,
            "clean": {
                "external_script": str(script_path),
                "external_mode": "execute"
            },
            "state": {}
        }
    )
    project_path: Path = _create_cache_project(tmp_path)
    args: argparse.Namespace = argparse.Namespace(target=str(project_path), dry_run=True, strategy=None)

    from seedlingtools.core.config_manager import SeedlingConfigManager
    from seedlingtools.utils.patterns import SingletonMeta
    if SeedlingConfigManager in SingletonMeta._instances:
        del SingletonMeta._instances[SeedlingConfigManager]

    with pytest.raises(ConfigurationError):
        handle_clean(args)
