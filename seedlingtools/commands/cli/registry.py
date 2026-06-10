from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Dict, Final, List

from .base import AbstractPluginCommand
from ...utils import PluginLoadError, SingletonMeta


class AbstractCommandRegistry(ABC):
    @abstractmethod
    def clear(self) -> None:
        pass

    @abstractmethod
    def register_command(self, command: AbstractPluginCommand, is_builtin: bool = False) -> None:
        pass

    @abstractmethod
    def get_command(self, command_name: str) -> AbstractPluginCommand:
        pass

    @abstractmethod
    def list_commands(self) -> List[AbstractPluginCommand]:
        pass

    @abstractmethod
    def has_command(self, command_name: str) -> bool:
        pass


class CommandRegistry(AbstractCommandRegistry, metaclass=SingletonMeta):
    def __init__(self) -> None:
        self._commands: Dict[str, AbstractPluginCommand] = {}
        self._builtins: Dict[str, bool] = {}

    def clear(self) -> None:
        self._commands.clear()
        self._builtins.clear()

    def register_command(self, command: AbstractPluginCommand, is_builtin: bool = False) -> None:
        command_name: str = command.command_name.strip()
        if len(command_name) == 0:
            raise PluginLoadError(message="Plugin command name cannot be empty.")

        if command_name in self._commands:
            if self._builtins.get(command_name, False) is True:
                raise PluginLoadError(
                    message=f"Plugin command '{command_name}' cannot override a built-in command.",
                    context={"command": command_name}
                )
            raise PluginLoadError(
                message=f"Duplicate plugin command name: {command_name}",
                context={"command": command_name}
            )

        self._commands[command_name] = command
        self._builtins[command_name] = is_builtin

    def get_command(self, command_name: str) -> AbstractPluginCommand:
        if command_name not in self._commands:
            raise PluginLoadError(
                message=f"Command is not registered: {command_name}",
                context={"command": command_name}
            )
        return self._commands[command_name]

    def list_commands(self) -> List[AbstractPluginCommand]:
        names: List[str] = sorted(self._commands.keys())
        commands: List[AbstractPluginCommand] = []
        for name in names:
            commands.append(self._commands[name])
        return commands

    def has_command(self, command_name: str) -> bool:
        return command_name in self._commands


command_registry: Final[AbstractCommandRegistry] = CommandRegistry()
