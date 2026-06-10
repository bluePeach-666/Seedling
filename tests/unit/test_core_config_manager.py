# Unit tests for Seedling-tools v2.5.
# Copyright (c) 2026 Kaelen Chow. All rights reserved.

from __future__ import annotations
import argparse
import json
from pathlib import Path
from typing import Any, Dict
from unittest.mock import patch

import pytest #type: ignore

from seedlingtools.core.config_manager import SeedlingConfigManager
from seedlingtools.utils import ConfigurationCorruptionError
from seedlingtools.utils.patterns import SingletonMeta


def _reset_config_singleton() -> None:
    if SeedlingConfigManager in SingletonMeta._instances:
        del SingletonMeta._instances[SeedlingConfigManager]


def _make_args(**overrides: Any) -> argparse.Namespace:
    values: Dict[str, Any] = {
        "depth": None,
        "no_hidden": None,
        "exclude": None,
        "include": None,
        "text_only": None,
        "type": None,
        "quiet": None,
        "regex": None,
        "ignore_case": None,
        "template": None
    }
    for key, value in overrides.items():
        values[key] = value
    return argparse.Namespace(**values)


@pytest.fixture(autouse=True)
def isolated_config_home(tmp_path: Path) -> None:
    _reset_config_singleton()
    home_path: Path = tmp_path / "home"
    home_path.mkdir()
    with patch.dict("os.environ", {"HOME": str(home_path), "USERPROFILE": str(home_path)}):
        yield
    _reset_config_singleton()


def test_config_first_run_initializes_global_file(tmp_path: Path) -> None:
    project_path: Path = tmp_path / "project"
    project_path.mkdir()
    manager: SeedlingConfigManager = SeedlingConfigManager()

    manager.initialize(cwd=project_path)

    config_path: Path = Path.home() / ".seedling" / "config.json"
    assert config_path.exists() is True
    loaded_config: Dict[str, Any] = json.loads(config_path.read_text(encoding="utf-8"))
    assert loaded_config["schema_version"] == 1
    assert loaded_config["scan"]["show_hidden"] is True
    assert loaded_config["commands"]["plugin_dirs"] == ["~/.seedling/plugins"]
    assert loaded_config["commands"]["autoload"] is True
    assert loaded_config["commands"]["strict"] is False
    assert loaded_config["state"] == {}


def test_config_loads_command_plugin_paths(tmp_path: Path) -> None:
    project_path: Path = tmp_path / "project"
    project_path.mkdir()
    config_dir: Path = Path.home() / ".seedling"
    config_dir.mkdir()
    config_file: Path = config_dir / "config.json"
    config_file.write_text(
        json.dumps({"schema_version": 1, "commands": {"plugin_dirs": ["~/plugins"], "strict": True}, "state": {}}),
        encoding="utf-8"
    )
    local_file: Path = project_path / ".seedling.json"
    local_file.write_text(
        json.dumps({"commands": {"plugin_dirs": ["./project_plugins"]}}),
        encoding="utf-8"
    )

    manager: SeedlingConfigManager = SeedlingConfigManager()
    manager.initialize(cwd=project_path)
    commands_section: Dict[str, Any] = manager.get_section("commands")

    assert commands_section["plugin_dirs"] == ["./project_plugins"]
    assert commands_section["strict"] is True


def test_config_rejects_non_list_command_plugin_paths(tmp_path: Path) -> None:
    project_path: Path = tmp_path / "project"
    project_path.mkdir()
    config_dir: Path = Path.home() / ".seedling"
    config_dir.mkdir()
    config_file: Path = config_dir / "config.json"
    config_file.write_text(
        json.dumps({"schema_version": 1, "commands": {"plugin_dirs": "~/plugins"}, "state": {}}),
        encoding="utf-8"
    )
    manager: SeedlingConfigManager = SeedlingConfigManager()

    with pytest.raises(ConfigurationCorruptionError):
        manager.initialize(cwd=project_path)


def test_config_loads_global_scan_defaults(tmp_path: Path) -> None:
    project_path: Path = tmp_path / "project"
    project_path.mkdir()
    config_dir: Path = Path.home() / ".seedling"
    config_dir.mkdir()
    config_file: Path = config_dir / "config.json"
    config_file.write_text(
        json.dumps({"schema_version": 1, "scan": {"max_depth": 2, "text_only": True}, "state": {}}),
        encoding="utf-8"
    )

    manager: SeedlingConfigManager = SeedlingConfigManager()
    manager.initialize(cwd=project_path)
    config = manager.build_scan_config(_make_args())

    assert config.max_depth == 2
    assert config.text_only is True
    assert config.show_hidden is True


def test_config_local_overrides_global_scan_values(tmp_path: Path) -> None:
    project_path: Path = tmp_path / "project"
    project_path.mkdir()
    config_dir: Path = Path.home() / ".seedling"
    config_dir.mkdir()
    config_file: Path = config_dir / "config.json"
    config_file.write_text(
        json.dumps({"schema_version": 1, "scan": {"max_depth": 5, "includes": ["*.py"]}, "state": {}}),
        encoding="utf-8"
    )
    local_file: Path = project_path / ".seedling.json"
    local_file.write_text(
        json.dumps({"scan": {"max_depth": 1, "show_hidden": False}}),
        encoding="utf-8"
    )

    manager: SeedlingConfigManager = SeedlingConfigManager()
    manager.initialize(cwd=project_path)
    config = manager.build_scan_config(_make_args())

    assert config.max_depth == 1
    assert config.show_hidden is False
    assert config.includes == ["*.py"]


def test_config_corrupt_global_json_raises_project_error(tmp_path: Path) -> None:
    project_path: Path = tmp_path / "project"
    project_path.mkdir()
    config_dir: Path = Path.home() / ".seedling"
    config_dir.mkdir()
    config_file: Path = config_dir / "config.json"
    config_file.write_text("{bad json", encoding="utf-8")
    manager: SeedlingConfigManager = SeedlingConfigManager()

    with pytest.raises(ConfigurationCorruptionError):
        manager.initialize(cwd=project_path)


def test_config_corrupt_local_json_raises_project_error(tmp_path: Path) -> None:
    project_path: Path = tmp_path / "project"
    project_path.mkdir()
    manager: SeedlingConfigManager = SeedlingConfigManager()
    manager.initialize(cwd=project_path)

    _reset_config_singleton()
    local_file: Path = project_path / ".seedling.json"
    local_file.write_text("{bad json", encoding="utf-8")
    manager = SeedlingConfigManager()

    with pytest.raises(ConfigurationCorruptionError):
        manager.initialize(cwd=project_path)


def test_config_non_object_json_raises_project_error(tmp_path: Path) -> None:
    project_path: Path = tmp_path / "project"
    project_path.mkdir()
    config_dir: Path = Path.home() / ".seedling"
    config_dir.mkdir()
    config_file: Path = config_dir / "config.json"
    config_file.write_text("[]", encoding="utf-8")
    manager: SeedlingConfigManager = SeedlingConfigManager()

    with pytest.raises(ConfigurationCorruptionError):
        manager.initialize(cwd=project_path)


def test_config_state_serializes_to_global_file(tmp_path: Path) -> None:
    project_path: Path = tmp_path / "project"
    project_path.mkdir()
    manager: SeedlingConfigManager = SeedlingConfigManager()
    manager.initialize(cwd=project_path)

    manager.update_state("last_command", "scan")
    manager.save()

    config_path: Path = Path.home() / ".seedling" / "config.json"
    loaded_config: Dict[str, Any] = json.loads(config_path.read_text(encoding="utf-8"))
    assert loaded_config["state"]["last_command"] == "scan"


def test_config_cli_args_override_local_and_global(tmp_path: Path) -> None:
    project_path: Path = tmp_path / "project"
    project_path.mkdir()
    config_dir: Path = Path.home() / ".seedling"
    config_dir.mkdir()
    config_file: Path = config_dir / "config.json"
    config_file.write_text(
        json.dumps({"schema_version": 1, "scan": {"max_depth": 5, "excludes": ["global"]}, "state": {}}),
        encoding="utf-8"
    )
    local_file: Path = project_path / ".seedling.json"
    local_file.write_text(
        json.dumps({"scan": {"max_depth": 3, "includes": ["*.py"]}}),
        encoding="utf-8"
    )

    manager: SeedlingConfigManager = SeedlingConfigManager()
    manager.initialize(cwd=project_path)
    config = manager.build_scan_config(_make_args(depth=1, exclude=["cli"], no_hidden=True))

    assert config.max_depth == 1
    assert config.excludes == ["cli"]
    assert config.includes == ["*.py"]
    assert config.show_hidden is False
