# Unit tests for Seedling-tools v2.5.
# Copyright (c) 2026 Kaelen Chow. All rights reserved.

from __future__ import annotations
import argparse
from pathlib import Path
from typing import List

import pytest #type: ignore

from seedlingtools.commands.cli import BUILTIN_COMMANDS
from seedlingtools.commands.cli.base import AbstractPluginCommand
from seedlingtools.commands.cli.loader import load_command_plugins
from seedlingtools.commands.cli.registry import CommandRegistry
from seedlingtools.utils import PluginLoadError


class DummyCommand(AbstractPluginCommand):
    @property
    def command_name(self) -> str:
        return "dummy"

    @property
    def description(self) -> str:
        return "Dummy command"

    def setup_arguments(self, parser: argparse.ArgumentParser) -> None:
        parser.add_argument("--flag", action="store_true")

    def execute(self, args: argparse.Namespace) -> None:
        assert isinstance(args, argparse.Namespace) is True
        return None


def _write_valid_plugin(plugin_dir: Path, command_name: str = "custom-audit") -> Path:
    plugin_file: Path = plugin_dir / "custom_audit.py"
    plugin_file.write_text(
        "from __future__ import annotations\n"
        "import argparse\n"
        "from seedlingtools.commands.cli import AbstractPluginCommand\n"
        "class CustomAuditCommand(AbstractPluginCommand):\n"
        "    @property\n"
        f"    def command_name(self) -> str:\n        return {command_name!r}\n"
        "    @property\n"
        "    def description(self) -> str:\n        return 'Custom audit command'\n"
        "    def setup_arguments(self, parser: argparse.ArgumentParser) -> None:\n"
        "        parser.add_argument('--label', default='local')\n"
        "    def execute(self, args: argparse.Namespace) -> None:\n"
        "        print(f'custom audit {args.label}')\n",
        encoding="utf-8"
    )
    return plugin_file


def test_builtin_commands_register_by_default() -> None:
    registry: CommandRegistry = CommandRegistry()
    registry.clear()

    for command in BUILTIN_COMMANDS:
        registry.register_command(command, is_builtin=True)

    command_names: List[str] = []
    for command in registry.list_commands():
        command_names.append(command.command_name)

    assert "scan" in command_names
    assert "build" in command_names
    assert "clean" in command_names


def test_valid_plugin_module_registers_command(tmp_path: Path) -> None:
    plugin_dir: Path = tmp_path / "plugins"
    plugin_dir.mkdir()
    _write_valid_plugin(plugin_dir)
    registry: CommandRegistry = CommandRegistry()
    registry.clear()

    load_command_plugins([str(plugin_dir)], registry, strict=True)

    assert registry.has_command("custom-audit") is True
    assert registry.get_command("custom-audit").description == "Custom audit command"


def test_non_subclass_module_is_ignored(tmp_path: Path) -> None:
    plugin_dir: Path = tmp_path / "plugins"
    plugin_dir.mkdir()
    plugin_file: Path = plugin_dir / "fake.py"
    plugin_file.write_text(
        "class FakeCommand:\n"
        "    command_name = 'fake-command'\n",
        encoding="utf-8"
    )
    registry: CommandRegistry = CommandRegistry()
    registry.clear()

    load_command_plugins([str(plugin_dir)], registry, strict=True)

    assert registry.has_command("fake-command") is False
    assert len(registry.list_commands()) == 0


def test_duplicate_plugin_name_cannot_override_builtin(tmp_path: Path) -> None:
    plugin_dir: Path = tmp_path / "plugins"
    plugin_dir.mkdir()
    _write_valid_plugin(plugin_dir, command_name="scan")
    registry: CommandRegistry = CommandRegistry()
    registry.clear()
    for command in BUILTIN_COMMANDS:
        registry.register_command(command, is_builtin=True)

    with pytest.raises(PluginLoadError):
        load_command_plugins([str(plugin_dir)], registry, strict=True)

    assert registry.has_command("scan") is True


def test_syntax_error_plugin_skips_in_non_strict_mode(tmp_path: Path) -> None:
    plugin_dir: Path = tmp_path / "plugins"
    plugin_dir.mkdir()
    plugin_file: Path = plugin_dir / "broken.py"
    plugin_file.write_text("def broken(:\n", encoding="utf-8")
    registry: CommandRegistry = CommandRegistry()
    registry.clear()

    load_command_plugins([str(plugin_dir)], registry, strict=False)

    assert len(registry.list_commands()) == 0


def test_syntax_error_plugin_raises_in_strict_mode(tmp_path: Path) -> None:
    plugin_dir: Path = tmp_path / "plugins"
    plugin_dir.mkdir()
    plugin_file: Path = plugin_dir / "broken.py"
    plugin_file.write_text("def broken(:\n", encoding="utf-8")
    registry: CommandRegistry = CommandRegistry()
    registry.clear()

    with pytest.raises(PluginLoadError):
        load_command_plugins([str(plugin_dir)], registry, strict=True)


def test_missing_plugin_directory_is_skipped(tmp_path: Path) -> None:
    registry: CommandRegistry = CommandRegistry()
    registry.clear()

    load_command_plugins([str(tmp_path / "missing")], registry, strict=True)

    assert len(registry.list_commands()) == 0
