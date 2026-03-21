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
    parser.add_argument("-F", "--format", choices=["md", "txt", "image", "json"], default="md", help="Output format")
    parser.add_argument("-n", "--name", help="Custom output filename")
    parser.add_argument("-o", "--outdir", help="Output directory path")
    parser.add_argument("-d", "--depth", type=int, default=None, help="Maximum recursion depth")
    parser.add_argument("-e", "--exclude", nargs="+", default=[], help="Files/directories to exclude")
    parser.add_argument("-v", "--verbose", action="store_true", help="Enable debug logging")
    parser.add_argument("-q", "--quiet", action="store_true", help="Only show errors")
    parser.add_argument("--showhidden", dest="show_hidden", action="store_true", help="Include hidden files")
    parser.add_argument("--text", dest="text_only", action="store_true", help="Only scan text files (ignore binary/media)")
    parser.add_argument("--delete", action="store_true", help="Delete matched items (FIND MODE ONLY)")
    parser.add_argument("--dry-run", dest="dry_run", action="store_true",
                        help="Preview deletions without executing (use with --delete)")
    parser.add_argument("--noemoji", dest="no_emoji", action="store_true", help="Disable emojis for legacy terminals")

    # NEW: Include filter
    parser.add_argument("--include", nargs="+", default=[], help="Only include files/directories matching patterns")

    # NEW: File type filter
    parser.add_argument("-t", "--type", type=str, default=None,
                        help="Filter by file type (py/js/ts/cpp/go/java/rs/web/json/yaml/md/shell/all)")

    # NEW: Regex mode for search
    parser.add_argument("--regex", action="store_true", help="Treat -f pattern as regular expression")

    # NEW: Grep mode (content search)
    grep_group = parser.add_argument_group("Grep Mode (Content Search)")
    grep_group.add_argument("-g", "--grep", type=str, default=None, dest="grep_pattern",
                            help="Search inside file contents")
    grep_group.add_argument("-C", "--context", type=int, default=0,
                            help="Show N lines of context around grep matches")
    grep_group.add_argument("-i", "--ignore-case", action="store_true",
                            help="Case-insensitive search (default is case-sensitive)")

    # NEW: Analyze mode
    parser.add_argument("--analyze", action="store_true", help="Analyze project structure and dependencies")

    output_mode = parser.add_mutually_exclusive_group()
    output_mode.add_argument(
        "--full",
        action="store_true",
        help="POWER MODE: Gather full text content of scanned files."
    )
    output_mode.add_argument(
        "--skeleton",
        action="store_true",
        help="[Experimental] AST Code Skeleton extraction (strips implementation logic)."
    )
    
def handle_scan(args):
    configure_logging(args.verbose, args.quiet)
    setup_ui_theme(args.no_emoji)

    if args.format == "image":
        try:
            import PIL # type: ignore
        except ImportError:
            print("\nERROR: 'Pillow' is required for image export.")
            print("Fix: pip install Pillow")
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

    # NEW: Analyze mode routing
    if args.analyze:
        from .analyzer import run_analyze
        run_analyze(args, target_path)
        return

    # NEW: Grep mode routing
    if args.grep_pattern:
        from .grep import run_grep
        run_grep(args, target_path)
        return

    if args.skeleton:
        # Check Python version for skeleton mode
        if sys.version_info < (3, 9):
            from seedling.core.logger import logger
            logger.error("Skeleton extraction requires Python 3.9 or higher.")
            logger.info(f"Current version: Python {sys.version_info.major}.{sys.version_info.minor}")
            logger.info("Tip: Use 'scan --full' for full source code export instead.")
            sys.exit(1)
        run_skeleton(args, target_path)
        return

    if args.find:
        run_search(args, target_path)
    else:
        run_explorer(args, target_path)