from __future__ import annotations
import sys
import argparse
import atexit
from pathlib import Path
from typing import Callable, Final, List

from .utils import (
    logger,
    terminal,
    get_package_version,
    SeedlingToolsError,
    gitter
)
from .core import config_manager
from .commands.scan import setup_scan_parser, handle_scan
from .commands.build import setup_build_parser, handle_build
from .commands.clean import setup_clean_parser, handle_clean
from .commands.cli import BUILTIN_COMMANDS, command_registry, load_command_plugins, register_generated_tools

def _initialize_config(cwd: Path, quiet_init: bool = False) -> None:
    logger.configure(verbose=False, quiet=False)
    config_manager.initialize(cwd=cwd, quiet_init=quiet_init)
    atexit.register(config_manager.save)


def _register_builtin_commands() -> None:
    command_registry.clear()
    for command in BUILTIN_COMMANDS:
        command_registry.register_command(command, is_builtin=True)


def _load_configured_command_plugins() -> None:
    commands_section = config_manager.get_section("commands")

    autoload: bool = True
    if "autoload" in commands_section:
        autoload = bool(commands_section["autoload"])

    if autoload is False:
        return

    strict: bool = False
    if "strict" in commands_section:
        strict = bool(commands_section["strict"])

    plugin_dirs: List[str] = []
    if "plugin_dirs" in commands_section:
        for raw_dir in commands_section["plugin_dirs"]:
            plugin_dirs.append(str(raw_dir))

    load_command_plugins(plugin_dirs, command_registry, strict=strict)
    register_generated_tools(Path.cwd(), command_registry)


def _build_root_parser() -> argparse.ArgumentParser:
    version_str: Final[str] = get_package_version()
    parser: argparse.ArgumentParser = argparse.ArgumentParser(
        prog="seedling",
        description=f"Seedling-tools (v{version_str}) - Project Intelligence CLI",
        formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument("--version", action="version", version=f"Seedling-tools v{version_str}")

    subparsers = parser.add_subparsers(dest="command")
    for command in command_registry.list_commands():
        subparser: argparse.ArgumentParser = subparsers.add_parser(
            command.command_name,
            description=command.description,
            help=command.description,
            formatter_class=argparse.RawTextHelpFormatter
        )
        command.setup_arguments(subparser)
        subparser.set_defaults(command_handler=command.execute)

    return parser


def main() -> None:
    terminal.configure_environment()

    try:
        _initialize_config(Path.cwd(), quiet_init=True)
        _register_builtin_commands()
        _load_configured_command_plugins()
        parser: argparse.ArgumentParser = _build_root_parser()
        args: argparse.Namespace = parser.parse_args()

        if hasattr(args, "command_handler") is False:
            parser.print_help()
            sys.exit(0)

        command_handler: Callable[[argparse.Namespace], None] = getattr(args, "command_handler")
        command_handler(args)
    except SeedlingToolsError as err:
        logger.error(str(err))
        sys.exit(err.exit_code)
    except KeyboardInterrupt:
        logger.info("\nOperation interrupted by user. Exiting Seedling-tools...")
        sys.exit(0)


def scan() -> None:
    terminal.configure_environment()
    
    version_str: Final[str] = get_package_version()
    parser: argparse.ArgumentParser = argparse.ArgumentParser(
        prog="scan",
        description=f"Seedling-tools Scan (v{version_str}) - Directory Explorer",
        formatter_class=argparse.RawTextHelpFormatter
    )
    setup_scan_parser(parser)

    try:
        args: argparse.Namespace = parser.parse_args()
        
        if _is_remote_url(args.target) is True:
            repo_path: Path = gitter.clone_repository(args.target)
            atexit.register(gitter.cleanup_repository, repo_path)
            args.target = str(repo_path)

        scan_cwd: Path = Path(args.target).resolve(strict=False)
        _initialize_config(scan_cwd)

        handle_scan(args)
    except SeedlingToolsError as err:
        logger.error(str(err))
        sys.exit(err.exit_code)
    except KeyboardInterrupt:
        logger.info("\nOperation interrupted by user. Exiting Seedling-tools...")
        sys.exit(0)

def build() -> None:
    terminal.configure_environment()

    version_str: Final[str] = get_package_version()
    parser: argparse.ArgumentParser = argparse.ArgumentParser(
        prog="build",
        description=f"Seedling-tools Build (v{version_str}) - Project Structure Builder",
        formatter_class=argparse.RawTextHelpFormatter
    )
    setup_build_parser(parser)

    try:
        args: argparse.Namespace = parser.parse_args()
        _initialize_config(Path.cwd())
        handle_build(args)
    except SeedlingToolsError as err:
        logger.error(str(err))
        sys.exit(err.exit_code)
    except KeyboardInterrupt:
        logger.info("\nOperation interrupted by user. Exiting Seedling-tools...")
        sys.exit(0)

def clean() -> None:
    terminal.configure_environment()

    version_str: Final[str] = get_package_version()
    parser: argparse.ArgumentParser = argparse.ArgumentParser(
        prog="clean",
        description=f"Seedling-tools Clean (v{version_str}) - Smart Cache Sweeper",
        formatter_class=argparse.RawTextHelpFormatter
    )
    setup_clean_parser(parser)

    try:
        args: argparse.Namespace = parser.parse_args()
        _initialize_config(Path.cwd())
        handle_clean(args)
    except SeedlingToolsError as err:
        logger.error(str(err))
        sys.exit(err.exit_code)
    except KeyboardInterrupt:
        logger.info("\nOperation interrupted by user. Exiting Seedling-tools...")
        sys.exit(0)

def _is_remote_url(target: str) -> bool:
    if target.startswith("http://") is True:
        return True
    elif target.startswith("https://") is True:
        return True
    elif target.startswith("git@") is True:
        return True
    else:
        return False