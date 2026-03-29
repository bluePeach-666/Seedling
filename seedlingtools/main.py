from __future__ import annotations
import sys
import argparse
from .utils import (
    logger,
    terminal,
    get_package_version,
    SeedlingToolsError
)
from .commands.scan import setup_scan_parser, handle_scan
from .commands.build import setup_build_parser, handle_build

def scan() -> None:
    """初始化并调度 scan 命令行入口"""
    terminal.configure_environment()
    
    # 实例化并配置 Parser
    parser = argparse.ArgumentParser(
        prog="scan",
        description=f"Seedling-tools Scan (v{get_package_version()}) - Directory Explorer",
        formatter_class=argparse.RawTextHelpFormatter
    )
    setup_scan_parser(parser)

    try:
        args: argparse.Namespace = parser.parse_args()
        if _is_remote_url(args.target):
            logger.warning(f"Remote repository support ({args.target}) is coming in v2.5.1!")
            logger.info("Please clone the repository locally to scan it with the current version.")
            sys.exit(0)
            
        handle_scan(args)
    except SeedlingToolsError as err:
        # 统一拦截所有已知领域异常
        logger.error(str(err))
        sys.exit(err.exit_code)
    except KeyboardInterrupt:
        logger.info("\nInterrupted by user. Exiting Seedling-tools...")
        sys.exit(0)


def build() -> None:
    """初始化并调度 build 命令行入口"""
    terminal.configure_environment()
    
    # 实例化并配置 Parser
    parser = argparse.ArgumentParser(
        prog="build",
        description=f"Seedling-tools Build (v{get_package_version()}) - Project Structure Builder",
        formatter_class=argparse.RawTextHelpFormatter
    )
    setup_build_parser(parser)

    try:
        args: argparse.Namespace = parser.parse_args()
        handle_build(args)
    except SeedlingToolsError as err:
        # 统一拦截所有已知领域异常
        logger.error(str(err))
        sys.exit(err.exit_code)
    except KeyboardInterrupt:
        logger.info("\nInterrupted by user. Exiting Seedling-tools...")
        sys.exit(0)

def _is_remote_url(target: str) -> bool:
    """判定是否为远程仓库地址"""
    return target.startswith(("http://", "https://", "git@"))