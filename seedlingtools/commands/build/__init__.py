"""
Build command entry for the Seedling-tools.  
Copyright (c) 2026 Kaelen Chow. All rights reserved.  
版权所有 © 2026 周珈民。保留一切权利。
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
    """build 命令行的 CLI 参数解析器"""
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
    """直接在文件系统中创建目标路径"""
    try:
        if not target_path.suffix:
            target_path.mkdir(parents=True, exist_ok=True)
            logger.info(f"Successfully created directory: {target_path}")
        else:
            if not target_path.parent.exists():
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
    """处理 build 命令的主入口"""
    no_color_flag: bool = getattr(args, 'no_color', False)
    verbose_flag: bool = getattr(args, 'verbose', False)
    quiet_flag: bool = getattr(args, 'quiet', False)
    terminal.configure_environment(no_color=no_color_flag)
    logger.configure(verbose=verbose_flag, quiet=quiet_flag)

    if not args.file:
        logger.info("Welcome to Build mode! Please provide a blueprint file (.md/.txt) to get started.")
        sys.exit(0)

    try:
        source_file: Path = Path(args.file).resolve()
        if source_file.is_dir():
            raise ConfigurationError(
                message=f"'{args.file}' is a DIRECTORY.",
                hint="The 'build' command requires a text or markdown FILE blueprint."
            )
            
        if args.direct:
            _handle_direct_creation(source_file)
            sys.exit(0)

        target_provided: bool = False
        if args.target is not None:
            target_provided = True

        target_dir: Path = Path.cwd()
        if target_provided:
            target_dir = Path(args.target).resolve()
            
        # 如果蓝图文件不存在，猜测用户可能是想用 build 命令直接新建文件/文件夹
        if not source_file.exists():
            logger.error(f"Blueprint file '{args.file}' does not exist.")
            
            # 如果用户还提供了 target，说明他的确是想执行规范的 build 流程，但把文件名写错了
            if target_provided:
                sys.exit(1)
                
            prompt: str = "Did you mean to directly create this path as a file/folder instead? [y/n]: "
            if terminal.prompt_confirmation(prompt):
                _handle_direct_creation(source_file)
                sys.exit(0)
            else:
                sys.exit(1)

        parser: TextBlueprintParser = TextBlueprintParser()
        executor: LocalFSExecutor = LocalFSExecutor()
        orchestrator: BuildOrchestrator = BuildOrchestrator(parser=parser, executor=executor)
        
        if args.check:
            plugin: DryRunPlugin = DryRunPlugin()
            orchestrator.add_plugin(plugin)

        force_flag: bool = getattr(args, 'force', False)
        success: bool = orchestrator.run_pipeline(source_file, target_dir, force_mode=force_flag)
        
        if not success:
            sys.exit(1)

    except SeedlingToolsError as err:
        logger.error(str(err))
        sys.exit(err.exit_code)
    except KeyboardInterrupt:
        logger.info("\nOperation interrupted by user.")
        sys.exit(0)