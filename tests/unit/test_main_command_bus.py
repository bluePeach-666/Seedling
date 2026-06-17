# Unit tests for Seedling-tools v2.5.
# Copyright (c) 2026 Kaelen Chow. All rights reserved.

from __future__ import annotations
import json
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest #type: ignore

from seedlingtools import main as seedling_main
from seedlingtools.commands.cli.registry import CommandRegistry
from seedlingtools.core.config_manager import SeedlingConfigManager
from seedlingtools.utils.patterns import SingletonMeta


def _reset_singletons() -> None:
    if SeedlingConfigManager in SingletonMeta._instances:
        del SingletonMeta._instances[SeedlingConfigManager]
    if CommandRegistry in SingletonMeta._instances:
        del SingletonMeta._instances[CommandRegistry]


def _write_plugin(plugin_dir: Path) -> None:
    plugin_file: Path = plugin_dir / "custom_audit.py"
    plugin_file.write_text(
        "from __future__ import annotations\n"
        "import argparse\n"
        "from seedlingtools.commands.cli import AbstractPluginCommand\n"
        "class CustomAuditCommand(AbstractPluginCommand):\n"
        "    @property\n"
        "    def command_name(self) -> str:\n        return 'custom-audit'\n"
        "    @property\n"
        "    def description(self) -> str:\n        return 'Custom audit command'\n"
        "    def setup_arguments(self, parser: argparse.ArgumentParser) -> None:\n"
        "        parser.add_argument('--label', default='local')\n"
        "    def execute(self, args: argparse.Namespace) -> None:\n"
        "        print(f'custom audit {args.label}')\n",
        encoding="utf-8"
    )


@pytest.fixture(autouse=True)
def isolated_cli_home(tmp_path: Path) -> None:
    _reset_singletons()
    home_path: Path = tmp_path / "home"
    home_path.mkdir()
    with patch.dict("os.environ", {"HOME": str(home_path), "USERPROFILE": str(home_path)}):
        yield
    _reset_singletons()


def test_seedling_root_help_includes_builtin_commands(capsys: Any) -> None:
    with patch("sys.argv", ["seedling"]):
        with pytest.raises(SystemExit) as err:
            seedling_main.main()

    captured = capsys.readouterr()
    assert err.value.code == 0
    assert "scan" in captured.out
    assert "build" in captured.out
    assert "clean" in captured.out
    assert "config" in captured.out
    assert "strip-comments" in captured.out
    assert "tools" in captured.out


def test_seedling_help_includes_loaded_plugin(tmp_path: Path, capsys: Any) -> None:
    plugin_dir: Path = tmp_path / "plugins"
    plugin_dir.mkdir()
    _write_plugin(plugin_dir)
    config_dir: Path = Path.home() / ".seedling"
    config_dir.mkdir()
    config_file: Path = config_dir / "config.json"
    config_file.write_text(
        json.dumps({"schema_version": 1, "commands": {"plugin_dirs": [str(plugin_dir)]}, "state": {}}),
        encoding="utf-8"
    )

    with patch("sys.argv", ["seedling"]):
        with pytest.raises(SystemExit):
            seedling_main.main()

    captured = capsys.readouterr()
    assert "custom-audit" in captured.out
    assert "Custom audit command" in captured.out


def test_plugin_help_includes_custom_arguments(tmp_path: Path, capsys: Any) -> None:
    plugin_dir: Path = tmp_path / "plugins"
    plugin_dir.mkdir()
    _write_plugin(plugin_dir)
    config_dir: Path = Path.home() / ".seedling"
    config_dir.mkdir()
    config_file: Path = config_dir / "config.json"
    config_file.write_text(
        json.dumps({"schema_version": 1, "commands": {"plugin_dirs": [str(plugin_dir)]}, "state": {}}),
        encoding="utf-8"
    )

    with patch("sys.argv", ["seedling", "custom-audit", "--help"]):
        with pytest.raises(SystemExit) as err:
            seedling_main.main()

    captured = capsys.readouterr()
    assert err.value.code == 0
    assert "--label" in captured.out


def test_dispatch_invokes_plugin_execute(tmp_path: Path, capsys: Any) -> None:
    plugin_dir: Path = tmp_path / "plugins"
    plugin_dir.mkdir()
    _write_plugin(plugin_dir)
    config_dir: Path = Path.home() / ".seedling"
    config_dir.mkdir()
    config_file: Path = config_dir / "config.json"
    config_file.write_text(
        json.dumps({"schema_version": 1, "commands": {"plugin_dirs": [str(plugin_dir)]}, "state": {}}),
        encoding="utf-8"
    )

    with patch("sys.argv", ["seedling", "custom-audit", "--label", "ci"]):
        seedling_main.main()

    captured = capsys.readouterr()
    assert "custom audit ci" in captured.out


def test_config_show_prints_preferences_json(capsys: Any) -> None:
    with patch("sys.argv", ["seedling", "config", "show"]):
        seedling_main.main()

    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert payload["output_format"] is None
    assert payload["common_excludes"] == []


def test_config_set_and_unset_round_trip(capsys: Any) -> None:
    with patch("sys.argv", ["seedling", "config", "set", "output_format", "json"]):
        seedling_main.main()
    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert payload["output_format"] == "json"

    with patch("sys.argv", ["seedling", "config", "unset", "output_format"]):
        seedling_main.main()
    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert payload["output_format"] is None


def test_config_reset_restores_defaults(capsys: Any) -> None:
    with patch("sys.argv", ["seedling", "config", "set", "show_hidden", "true"]):
        seedling_main.main()
    _ = capsys.readouterr()

    with patch("sys.argv", ["seedling", "config", "reset"]):
        seedling_main.main()
    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert payload["show_hidden"] is None


def test_strip_comments_check_reports_token_savings(tmp_path: Path, capsys: Any) -> None:
    source_file: Path = tmp_path / "example.py"
    source_file.write_text("# remove\nvalue = 1\n", encoding="utf-8")

    with patch("sys.argv", ["seedling", "strip-comments", str(source_file), "--check"]):
        seedling_main.main()

    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert payload["path"] == str(source_file)
    assert "saved_tokens" in payload


def test_unknown_seedling_command_exits_with_argparse_error() -> None:
    with patch("sys.argv", ["seedling", "missing-command"]):
        with pytest.raises(SystemExit) as err:
            seedling_main.main()

    assert err.value.code == 2


def test_legacy_entrypoints_still_build_parsers() -> None:
    with patch("sys.argv", ["scan", "--help"]):
        with pytest.raises(SystemExit) as scan_exit:
            seedling_main.scan()
    with patch("sys.argv", ["build", "--help"]):
        with pytest.raises(SystemExit) as build_exit:
            seedling_main.build()
    with patch("sys.argv", ["clean", "--help"]):
        with pytest.raises(SystemExit) as clean_exit:
            seedling_main.clean()

    assert scan_exit.value.code == 0
    assert build_exit.value.code == 0
    assert clean_exit.value.code == 0
