from __future__ import annotations
import inspect
import importlib.util
from pathlib import Path
from types import ModuleType
from typing import List, Optional

from .base import AbstractPluginCommand
from .registry import AbstractCommandRegistry
from ...utils import PluginLoadError, logger


def load_command_plugins(
    plugin_dirs: List[str],
    registry: AbstractCommandRegistry,
    strict: bool = False
) -> None:
    for raw_dir in plugin_dirs:
        plugin_dir: Path = Path(raw_dir).expanduser()
        if plugin_dir.exists() is False:
            continue
        if plugin_dir.is_dir() is False:
            _handle_plugin_error(
                PluginLoadError(
                    message=f"Plugin path is not a directory: {plugin_dir}",
                    context={"path": str(plugin_dir)}
                ),
                strict
            )
            continue

        plugin_files: List[Path] = sorted(plugin_dir.glob("*.py"))
        for plugin_file in plugin_files:
            if plugin_file.name.startswith("_") is True:
                continue
            try:
                module: ModuleType = _load_module_from_path(plugin_file)
                _register_module_commands(module, registry)
            except PluginLoadError as err:
                _handle_plugin_error(err, strict)
            except Exception as err:
                wrapped_error: PluginLoadError = PluginLoadError(
                    message=f"Failed to load plugin module: {plugin_file}",
                    context={"path": str(plugin_file), "error": str(err)}
                )
                _handle_plugin_error(wrapped_error, strict)


def _load_module_from_path(plugin_file: Path) -> ModuleType:
    module_name: str = f"seedling_user_plugin_{plugin_file.stem}"
    spec: Optional[importlib.machinery.ModuleSpec] = importlib.util.spec_from_file_location(module_name, plugin_file)
    if spec is None:
        raise PluginLoadError(
            message=f"Failed to create import spec for plugin: {plugin_file}",
            context={"path": str(plugin_file)}
        )
    if spec.loader is None:
        raise PluginLoadError(
            message=f"Plugin import loader is unavailable: {plugin_file}",
            context={"path": str(plugin_file)}
        )

    module: ModuleType = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(module)
    except SyntaxError as err:
        raise PluginLoadError(
            message=f"Plugin has invalid Python syntax: {plugin_file}",
            context={"path": str(plugin_file), "error": str(err)}
        ) from err
    except Exception as err:
        raise PluginLoadError(
            message=f"Plugin import failed: {plugin_file}",
            context={"path": str(plugin_file), "error": str(err)}
        ) from err

    return module


def _register_module_commands(module: ModuleType, registry: AbstractCommandRegistry) -> None:
    for _name, value in inspect.getmembers(module, inspect.isclass):
        if issubclass(value, AbstractPluginCommand) is False:
            continue
        if value is AbstractPluginCommand:
            continue
        if inspect.isabstract(value) is True:
            continue
        command: AbstractPluginCommand = value()
        registry.register_command(command, is_builtin=False)


def _handle_plugin_error(error: PluginLoadError, strict: bool) -> None:
    if strict is True:
        raise error
    logger.warning(str(error))
