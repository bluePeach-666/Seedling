import sys
from pathlib import Path
from seedling import __version__
from seedling.core.ui import handle_empty_run
from seedling.core.io import handle_path_error
from .explorer import run_explorer
from .search import run_search
from .skeleton import run_skeleton

def setup_scan_parser(parser):
    parser.add_argument("--version", action="version", version=f"Seedling v{__version__}")
    parser.add_argument("target", nargs="?", default=".", help="Target directory for scanning or searching")
    parser.add_argument("-f", "--find", type=str, help="FIND MODE: Search items (Exact & Fuzzy)")
    parser.add_argument("-F", "--format", choices=["md", "txt", "image"], default="md", help="Output format")
    parser.add_argument("-n", "--name", help="Custom output filename")
    parser.add_argument("-o", "--outdir", help="Output directory path")
    parser.add_argument("-d", "--depth", type=int, default=None, help="Maximum recursion depth")
    parser.add_argument("-e", "--exclude", nargs="+", default=[], help="Files/directories to exclude")
    parser.add_argument("--show", dest="show_hidden", action="store_true", help="Include hidden files")
    parser.add_argument("--text", dest="text_only", action="store_true", help="Only scan text files (ignore binary/media)")
    parser.add_argument("--full", action="store_true", help="POWER MODE: Gather full content")
    parser.add_argument("--delete", action="store_true", help="Delete matched items (FIND MODE ONLY)")
    parser.add_argument("--skeleton", action="store_true", help="[实验性] 提取代码骨架")

def handle_scan(args):
    # Process Empty Execution (Easter Eggs)
    if args.target == "." and len(sys.argv) <= 1:
        handle_empty_run()
        return

    if args.skeleton:
        run_skeleton()
        return

    target_path = Path(args.target).resolve()
    if not target_path.exists() or not target_path.is_dir():
        handle_path_error(args.target)

    if args.find:
        run_search(args, target_path)
    else:
        run_explorer(args, target_path)