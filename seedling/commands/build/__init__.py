import sys
from pathlib import Path
from seedling import __version__ 
from seedling.core.ui import handle_empty_build_run, ask_yes_no
from .architect import build_structure_from_file

def setup_build_parser(parser):
    parser.add_argument("--version", action="version", version=f"Seedling v{__version__}")
    parser.add_argument("file", nargs="?", help="The source tree file (.txt or .md)")
    parser.add_argument("target", nargs="?", default=None, help="Where to build the structure (default: current dir)")
    parser.add_argument("-d", "--direct", action="store_true", help="Directly create the path without prompting")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--check", action="store_true", help="Dry-run: Check what is missing before building")
    group.add_argument("--force", action="store_true", help="Force overwrite existing files")

def handle_build(args):
    if not args.file:
        handle_empty_build_run()
        return

    source_file = Path(args.file).resolve()
    
    if source_file.is_dir():
        print(f"\n❌ ERROR: '{args.file}' is a DIRECTORY. The 'build' command requires a text/markdown FILE blueprint.")
        sys.exit(1)
        
    if args.direct:
        if not source_file.suffix:
            source_file.mkdir(parents=True, exist_ok=True)
            print(f"✅ Successfully created directory: {source_file}")
        else:
            source_file.parent.mkdir(parents=True, exist_ok=True)
            source_file.touch(exist_ok=True)
            print(f"✅ Successfully created file: {source_file}")
        sys.exit(0)

    target_provided = args.target is not None
    target_dir = Path(args.target).resolve() if target_provided else Path(".").resolve()
    
    if not source_file.exists():
        print(f"\n❌ ERROR: Blueprint file '{args.file}' does not exist.")
        if target_provided:
            sys.exit(1)
            
        if ask_yes_no(f"👉 Did you mean to directly create this path as a file/folder instead? [y/n]: "):
            if not source_file.suffix:
                source_file.mkdir(parents=True, exist_ok=True)
                print(f"✅ Successfully created directory: {source_file}")
            else:
                source_file.parent.mkdir(parents=True, exist_ok=True)
                source_file.touch(exist_ok=True)
                print(f"✅ Successfully created file: {source_file}")
            sys.exit(0)
        else:
            sys.exit(1)
            
    build_structure_from_file(source_file, target_dir, check_mode=args.check, force_mode=args.force)