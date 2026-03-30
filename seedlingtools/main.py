from __future__ import annotations
import sys
import argparse
import atexit
from pathlib import Path
from typing import Final

from .utils import (
    logger,
    terminal,
    get_package_version,
    SeedlingToolsError,
    gitter
)
from .commands.scan import setup_scan_parser, handle_scan
from .commands.build import setup_build_parser, handle_build

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
        handle_build(args)
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