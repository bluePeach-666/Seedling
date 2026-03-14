import argparse
import sys
from seedling import __version__
from seedling.commands.scan import setup_scan_parser, handle_scan
from seedling.commands.build import setup_build_parser, handle_build
from seedling.core.ui import ensure_utf8_output

def scan():
    ensure_utf8_output()
    parser = argparse.ArgumentParser(
        description=f"🌲 Seedling Scan (v{__version__}) - Directory Explorer",
        formatter_class=argparse.RawTextHelpFormatter,
        prog="scan"
    )
    setup_scan_parser(parser)
    try:
        args = parser.parse_args()
        handle_scan(args)
    except KeyboardInterrupt:
        print("\n\n👋 Interrupted by user. Exiting Seedling...")
        sys.exit(0)

def build():
    parser = argparse.ArgumentParser(
        description=f"🏗️ Seedling Build (v{__version__}) - Project Structure Builder",
        formatter_class=argparse.RawTextHelpFormatter,
        prog="build"
    )
    setup_build_parser(parser)
    try:
        args = parser.parse_args()
        handle_build(args)
    except KeyboardInterrupt:
        print("\n\n👋 Interrupted by user. Exiting Seedling...")
        sys.exit(0)