"""
Scan command entry for the Seedling-tools.  
Copyright (c) 2026 Kaelen Chow. All rights reserved.  
版权所有 © 2026 周珈民。保留一切权利。
"""

from __future__ import annotations
import sys
import argparse
from pathlib import Path
from typing import List
from .helper import expand_scan_excludes
from .explorer import ScanOrchestrator
from .exporters import TextExporter, JsonExporter, XmlExporter
from .plugins import AnalyzerPlugin, GrepPlugin, SearchPlugin, SkeletonPlugin
from .base import AbstractScanPlugin, AbstractExporter
from ...core import ScanConfig, DepthFirstTraverser, TraversalResult
from ...utils import (
    logger,
    terminal,
    get_package_version,
    SeedlingToolsError,
    ConfigurationError
)

__all__ = [
    "setup_scan_parser",
    "handle_scan",
    "ScanOrchestrator",
    "AbstractScanPlugin",
    "AbstractExporter",
    "TextExporter",
    "JsonExporter",
    "AnalyzerPlugin",
    "GrepPlugin",
    "SearchPlugin",
    "SkeletonPlugin"
]

def setup_scan_parser(parser: argparse.ArgumentParser) -> None:
    """scan 命令行的 CLI 参数解析器"""
    parser.add_argument("--version", action="version", version=f"Seedling-tools v{get_package_version()}")
    parser.add_argument("target", nargs="?", default=".", help="Target directory for scanning or searching")
    parser.add_argument("-F", "--format", choices=["md", "txt", "image", "json", "xml"], default="md", help="Output format")
    parser.add_argument("-n", "--name", type=str, help="Custom output filename")
    parser.add_argument("-o", "--outdir", type=str, help="Output directory path")
    parser.add_argument("-d", "--depth", type=int, default=None, help="Maximum recursion depth")
    parser.add_argument("-e", "--exclude", nargs="+", default=[], help="Files/directories to exclude")
    parser.add_argument("--include", nargs="+", default=[], help="Only include files/directories matching patterns")
    parser.add_argument("-t", "--type", type=str, default=None, help="Filter by file type (py/js/ts/cpp/go/java/rs/web/json/yaml/md/shell/all)")
    parser.add_argument("--showhidden", dest="show_hidden", action="store_true", help="Include hidden files")
    parser.add_argument("--text", dest="text_only", action="store_true", help="Only scan text files (ignore binary/media)")
    parser.add_argument("-v", "--verbose", action="store_true", help="Enable debug logging")
    parser.add_argument("-q", "--quiet", action="store_true", help="Only show errors")
    parser.add_argument("--no-color", action="store_true", help="Disable terminal colors and rich formatting")
    parser.add_argument("-f", "--find", type=str, help="FIND MODE: Search items (Exact & Fuzzy)")
    parser.add_argument("--delete", action="store_true", help="Delete matched items (FIND MODE ONLY)")
    parser.add_argument("--dry-run", dest="dry_run", action="store_true", help="Preview deletions without executing (use with --delete)")
    parser.add_argument("--regex", action="store_true", help="Treat -f/-g pattern as regular expression")
    grep_group = parser.add_argument_group("Grep Mode (Content Search)")
    grep_group.add_argument("-g", "--grep", type=str, default=None, dest="grep_pattern", help="Search inside file contents")
    grep_group.add_argument("-C", "--context", type=int, default=0, help="Show N lines of context around grep matches")
    grep_group.add_argument("-i", "--ignore-case", action="store_true", help="Case-insensitive search")
    parser.add_argument("--analyze", action="store_true", help="Analyze project structure and dependencies")
    output_mode = parser.add_mutually_exclusive_group()
    output_mode.add_argument("--full", action="store_true", help="POWER MODE: Gather full text content of scanned files.")
    output_mode.add_argument("--skeleton", action="store_true", help="[Experimental] AST Code Skeleton extraction.")


def handle_scan(args: argparse.Namespace) -> None:
    """处理 scan 命令的主入口"""
    terminal.configure_environment(no_color=getattr(args, 'no_color', False))
    logger.configure(verbose=getattr(args, 'verbose', False), quiet=getattr(args, 'quiet', False))
    if len(sys.argv) == 1:
        terminal.display_banner()
        sys.exit(0)

    try:
        target_path: Path = Path(args.target).resolve(strict=True)
        if not target_path.is_dir():
            raise ConfigurationError(
                message=f"Target path '{args.target}' is not a valid directory.",
                hint="Please provide a valid folder path to scan."
            )

        excludes: List[str] = expand_scan_excludes(args.exclude) if args.exclude else []
        grep_pattern: str | None = getattr(args, 'grep_pattern', None)
        needs_content: bool = bool(args.full or grep_pattern or args.analyze or args.skeleton)
        
        auto_show_hidden: bool = args.show_hidden
        if args.find:
            if args.find.startswith('.'):
                auto_show_hidden = True

        config = ScanConfig(
            max_depth=args.depth,
            show_hidden=auto_show_hidden,
            excludes=excludes,
            includes=getattr(args, 'include', []),
            file_type=getattr(args, 'type', None),
            text_only=args.text_only or (grep_pattern is not None),
            quiet=args.quiet,
            use_regex=getattr(args, 'regex', False),
            ignore_case=args.ignore_case
        )

        if not args.quiet:
            logger.info(f"Scanning directory topology in '{target_path.name}'...")

        traverser = DepthFirstTraverser()
        result: TraversalResult = traverser.traverse(target_path, config, collect_content=needs_content)

        if not args.quiet:
            sys.stdout.write(f"\rScan Complete! [ {result.stats['dirs']} dirs | {result.stats['files']} files ]            \n")
            sys.stdout.flush()

        exporter: AbstractExporter
        if args.format == 'json':
            exporter = JsonExporter()
        elif args.format == 'xml':
            exporter = XmlExporter()
        else:
            exporter = TextExporter(format_type=args.format)
        orchestrator = ScanOrchestrator(exporter=exporter)

        if args.analyze:
            orchestrator.add_plugin(AnalyzerPlugin())
            
        if grep_pattern:
            orchestrator.add_plugin(
                GrepPlugin(
                    pattern=grep_pattern, 
                    context_lines=args.context, 
                    ignore_case=args.ignore_case, 
                    format_type=args.format
                )
            )
            
        if args.skeleton:
            orchestrator.add_plugin(SkeletonPlugin())
            
        if args.find:
            orchestrator.add_plugin(
                SearchPlugin(
                    keyword=args.find, 
                    delete_mode=args.delete, 
                    dry_run=args.dry_run
                )
            )

        out_dir: Path = Path(args.outdir).resolve() if args.outdir else Path.cwd()
        out_dir.mkdir(parents=True, exist_ok=True)
        
        if args.name:
            out_file = out_dir / args.name
        else:
            ext_map: dict[str, str] = {'md': '.md', 'txt': '.txt', 'image': '.png', 'json': '.json'}
            suffix: str = ext_map.get(args.format, '.md')

            modifier = ""
            if args.analyze:
                modifier = "_analysis"
                suffix = ".md"
            elif args.skeleton:
                modifier = "_skeleton"
                suffix = ".md"
            elif grep_pattern:
                modifier = "_grep"
            elif args.find:
                modifier = f"_search_{args.find}"
                
            out_file = out_dir / f"{target_path.name}{modifier}{suffix}"

        orchestrator.run_pipeline(target_path, config, result, out_file=out_file, is_full=args.full)

    except SeedlingToolsError as err:
        logger.error(str(err))
        sys.exit(err.exit_code)
    except KeyboardInterrupt:
        logger.info("\nOperation interrupted by user.")
        sys.exit(0)