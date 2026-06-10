from __future__ import annotations
import argparse
import atexit
from pathlib import Path
from typing import Final, Tuple

from .base import AbstractPluginCommand
from ..scan import setup_scan_parser, handle_scan
from ..build import setup_build_parser, handle_build
from ..clean import setup_clean_parser, handle_clean
from ...core import config_manager
from ...utils import gitter


class ScanCommand(AbstractPluginCommand):
    @property
    def command_name(self) -> str:
        return "scan"

    @property
    def description(self) -> str:
        return "Directory explorer and context exporter"

    def setup_arguments(self, parser: argparse.ArgumentParser) -> None:
        setup_scan_parser(parser)

    def execute(self, args: argparse.Namespace) -> None:
        if _is_remote_url(args.target) is True:
            repo_path: Path = gitter.clone_repository(args.target)
            atexit.register(gitter.cleanup_repository, repo_path)
            args.target = str(repo_path)

        scan_cwd: Path = Path(args.target).resolve(strict=False)
        config_manager.initialize(cwd=scan_cwd)
        handle_scan(args)


class BuildCommand(AbstractPluginCommand):
    @property
    def command_name(self) -> str:
        return "build"

    @property
    def description(self) -> str:
        return "Project structure builder"

    def setup_arguments(self, parser: argparse.ArgumentParser) -> None:
        setup_build_parser(parser)

    def execute(self, args: argparse.Namespace) -> None:
        handle_build(args)


class CleanCommand(AbstractPluginCommand):
    @property
    def command_name(self) -> str:
        return "clean"

    @property
    def description(self) -> str:
        return "Smart cache sweeper"

    def setup_arguments(self, parser: argparse.ArgumentParser) -> None:
        setup_clean_parser(parser)

    def execute(self, args: argparse.Namespace) -> None:
        handle_clean(args)


BUILTIN_COMMANDS: Final[Tuple[AbstractPluginCommand, ...]] = (
    ScanCommand(),
    BuildCommand(),
    CleanCommand()
)


def _is_remote_url(target: str) -> bool:
    if target.startswith("http://") is True:
        return True
    elif target.startswith("https://") is True:
        return True
    elif target.startswith("git@") is True:
        return True
    else:
        return False
