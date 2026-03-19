import sys
from pathlib import Path
from seedling import __version__
from seedling.core.ui import handle_empty_run, setup_ui_theme
from seedling.core.io import handle_path_error
from seedling.core.logger import configure_logging
from .explorer import run_explorer
from .search import run_search
from .skeleton import run_skeleton
from .exclude import expand_excludes

def setup_scan_parser(parser):
    parser.add_argument("--version", action="version", version=f"Seedling v{__version__}")
    parser.add_argument("target", nargs="?", default=".", help="Target directory for scanning or searching")
    parser.add_argument("-f", "--find", type=str, help="FIND MODE: Search items (Exact & Fuzzy)")
    parser.add_argument("-F", "--format", choices=["md", "txt", "image"], default="md", help="Output format")
    parser.add_argument("-n", "--name", help="Custom output filename")
    parser.add_argument("-o", "--outdir", help="Output directory path")
    parser.add_argument("-d", "--depth", type=int, default=None, help="Maximum recursion depth")
    parser.add_argument("-e", "--exclude", nargs="+", default=[], help="Files/directories to exclude")
    parser.add_argument("-v", "--verbose", action="store_true", help="Enable debug logging")
    parser.add_argument("-q", "--quiet", action="store_true", help="Only show errors")
    parser.add_argument("--showhidden", dest="show_hidden", action="store_true", help="Include hidden files")
    parser.add_argument("--text", dest="text_only", action="store_true", help="Only scan text files (ignore binary/media)")
    parser.add_argument("--full", action="store_true", help="POWER MODE: Gather full content")
    parser.add_argument("--delete", action="store_true", help="Delete matched items (FIND MODE ONLY)")
    parser.add_argument("--skeleton", action="store_true", help="[Experimental] AST Code Skeleton extraction")
    parser.add_argument("--noemoji", dest="no_emoji", action="store_true", help="Disable emojis for legacy terminals")

def handle_scan(args):
    configure_logging(args.verbose, args.quiet)
    setup_ui_theme(args.no_emoji)

    if args.format == "image":
        try:
            import PIL # type: ignore
        except ImportError:
            print("\n❌ ERROR: 'Pillow' is required for image export.")
            print("👉 Fix: pip install Pillow")
            sys.exit(1)

    # Process Empty Execution (Easter Eggs)
    if args.target == "." and len(sys.argv) <= 1:
        handle_empty_run()
        return

    target_path = Path(args.target).resolve()
    if not target_path.exists() or not target_path.is_dir():
        handle_path_error(args.target)

    if args.exclude:
        args.exclude = expand_excludes(args.exclude)

    if args.skeleton:
        run_skeleton(args, target_path)
        return

    if args.find:
        run_search(args, target_path)
    else:
        run_explorer(args, target_path)