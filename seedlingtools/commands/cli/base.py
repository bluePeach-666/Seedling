from __future__ import annotations
import argparse
from abc import ABC, abstractmethod


class AbstractPluginCommand(ABC):
    @property
    @abstractmethod
    def command_name(self) -> str:
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        pass

    @abstractmethod
    def setup_arguments(self, parser: argparse.ArgumentParser) -> None:
        pass

    @abstractmethod
    def execute(self, args: argparse.Namespace) -> None:
        pass
