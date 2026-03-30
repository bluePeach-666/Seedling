"""
Build command entry for the Seedling-tools.  
Copyright (c) 2026 Kaelen Chow. All rights reserved.  
"""

from __future__ import annotations
import sys
import argparse
from pathlib import Path

from .architect import BuildOrchestrator
from .parsers import TextBlueprintParser
from .executors import LocalFSExecutor
from .plugins import DryRunPlugin
from ...utils import (
    logger,
    terminal,
    get_package_version,
    SeedlingToolsError,
    ConfigurationError,
    FileSystemError
)

__all__ = [
    "setup_build_parser",
    "handle_build",
    "BuildOrchestrator",
    "TextBlueprintParser",
    "LocalFSExecutor",
    "DryRunPlugin"
]

def setup_build_parser(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--version", action="version", version=f"Seedling-tools v{get_package_version()}")
    parser.add_argument("file", nargs="?", help="The source tree blueprint file (.txt or .md)")
    parser.add_argument("target", nargs="?", default=None, help="Where to build the structure (default: current dir)")
    parser.add_argument("-d", "--direct", action="store_true", help="Directly create the path without prompting")
    parser.add_argument("-v", "--verbose", action="store_true", help="Enable debug logging")
    parser.add_argument("-q", "--quiet", action="store_true", help="Only show errors")
    parser.add_argument("--no-color", action="store_true", help="Disable terminal colors and rich formatting")
    
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--check", action="store_true", help="Dry-run mode: Check what is missing before building")
    group.add_argument("--force", action="store_true", help="Force mode: Overwrite existing files unconditionally")


def _handle_direct_creation(target_path: Path) -> None:
    try:
        if len(target_path.suffix) == 0:
            target_path.mkdir(parents=True, exist_ok=True)
            logger.info(f"Successfully created directory: {target_path}")
        else:
            if target_path.parent.exists() is False:
                target_path.parent.mkdir(parents=True, exist_ok=True)
            target_path.touch(exist_ok=True)
            logger.info(f"Successfully created file: {target_path}")
    except OSError as err:
        raise FileSystemError(
            message=f"Failed to create path directly: {target_path.name}",
            hint="Check parent directory permissions.",
            context={"path": str(target_path)}
        ) from err


def handle_build(args: argparse.Namespace) -> None:
    no_color_flag: bool = False
    if hasattr(args, 'no_color') is True:
        if getattr(args, 'no_color') is True:
            no_color_flag = True
            
    verbose_flag: bool = False
    if hasattr(args, 'verbose') is True:
        if getattr(args, 'verbose') is True:
            verbose_flag = True
            
    quiet_flag: bool = False
    if hasattr(args, 'quiet') is True:
        if getattr(args, 'quiet') is True:
            quiet_flag = True
            
    terminal.configure_environment(no_color=no_color_flag)
    logger.configure(verbose=verbose_flag, quiet=quiet_flag)

    if args.file is None:
        logger.info("Welcome to Build mode! Please provide a blueprint file (.md/.txt) to get started.")
        sys.exit(0)

    try:
        source_file: Path = Path(args.file).resolve()
        if source_file.is_dir() is True:
            raise ConfigurationError(
                message=f"'{args.file}' is a DIRECTORY.",
                hint="The 'build' command requires a text or markdown FILE blueprint."
            )
            
        if args.direct is True:
            _handle_direct_creation(source_file)
            sys.exit(0)

        target_provided: bool = False
        if args.target is not None:
            target_provided = True

        target_dir: Path = Path.cwd()
        if target_provided is True:
            target_dir = Path(args.target).resolve()
            
        if source_file.exists() is False:
            logger.error(f"Blueprint file '{args.file}' does not exist.")
            
            if target_provided is True:
                sys.exit(1)
                
            prompt: str = "Did you mean to directly create this path as a file/folder instead? [y/n]: "
            if terminal.prompt_confirmation(prompt) is True:
                _handle_direct_creation(source_file)
                sys.exit(0)
            else:
                sys.exit(1)

        parser: TextBlueprintParser = TextBlueprintParser()
        executor: LocalFSExecutor = LocalFSExecutor()
        orchestrator: BuildOrchestrator = BuildOrchestrator(parser=parser, executor=executor)
        
        if args.check is True:
            plugin: DryRunPlugin = DryRunPlugin()
            orchestrator.add_plugin(plugin)

        force_flag: bool = False
        if hasattr(args, 'force') is True:
            if getattr(args, 'force') is True:
                force_flag = True
                
        success: bool = orchestrator.run_pipeline(source_file, target_dir, force_mode=force_flag)
        
        if success is False:
            sys.exit(1)

    except SeedlingToolsError as err:
        logger.error(str(err))
        sys.exit(err.exit_code)
    except KeyboardInterrupt:
        logger.info("\nOperation interrupted by user.")
        sys.exit(0)