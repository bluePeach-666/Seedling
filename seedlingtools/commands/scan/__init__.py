"""
Scan command entry for the Seedling-tools.
Copyright (c) 2026 Kaelen Chow. All rights reserved.
"""

from __future__ import annotations
import sys
import argparse
from pathlib import Path
from typing import List, Optional, Dict, Any

from .helper import expand_scan_excludes, intercept_garbage_files
from .explorer import ScanOrchestrator
from .exporters import TextExporter, JsonExporter, XmlExporter
from .plugins import AnalyzerPlugin, ContextInjectorPlugin, GrepPlugin, SearchPlugin, SkeletonPlugin
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
    "XmlExporter",
    "AnalyzerPlugin",
    "ContextInjectorPlugin",
    "GrepPlugin",
    "SearchPlugin",
    "SkeletonPlugin"
]

def setup_scan_parser(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--version", action="version", version=f"Seedling-tools v{get_package_version()}")
    parser.add_argument("target", nargs="?", default=".", help="Target directory for scanning or searching")
    parser.add_argument("-F", "--format", choices=["md", "txt", "image", "json", "xml"], default="md", help="Output format")
    parser.add_argument("-n", "--name", type=str, help="Custom output filename")
    parser.add_argument("-o", "--outdir", type=str, help="Output directory path")
    parser.add_argument("-d", "--depth", type=int, default=None, help="Maximum recursion depth")
    parser.add_argument("-e", "--exclude", nargs="+", default=[], help="Files/directories to exclude")
    parser.add_argument("--include", nargs="+", default=[], help="Only include files/directories matching patterns")
    parser.add_argument("-t", "--type", type=str, default=None, help="Filter by file type")
    parser.add_argument("--nohidden", dest="no_hidden", action="store_true", help="Do not scan hidden files")
    parser.add_argument("--text", dest="text_only", action="store_true", help="Only scan text files")
    parser.add_argument("-v", "--verbose", action="store_true", help="Enable debug logging")
    parser.add_argument("-q", "--quiet", action="store_true", help="Only show errors")
    parser.add_argument("--no-color", action="store_true", help="Disable terminal colors")
    parser.add_argument("-f", "--find", type=str, help="FIND MODE: Search items")
    parser.add_argument("--delete", action="store_true", help="Delete matched items (FIND MODE ONLY)")
    parser.add_argument("--dry-run", dest="dry_run", action="store_true", help="Preview deletions without executing")
    parser.add_argument("--regex", action="store_true", help="Treat -f/-g pattern as regular expression")
    
    grep_group = parser.add_argument_group("Grep Mode (Content Search)")
    grep_group.add_argument("-g", "--grep", type=str, default=None, dest="grep_pattern", help="Search inside file contents")
    grep_group.add_argument("-C", "--context", type=int, default=0, help="Show N lines of context around grep matches")
    grep_group.add_argument("-i", "--ignore-case", action="store_true", help="Case-insensitive search")
    
    parser.add_argument("--analyze", action="store_true", help="Analyze project structure and dependencies")
    parser.add_argument("--template", type=str, default=None, help="Provide a prompt template file for LLM context aggregation")
    
    output_mode = parser.add_mutually_exclusive_group()
    output_mode.add_argument("--full", action="store_true", help="Gather full text content of scanned files.")
    output_mode.add_argument("--skeleton", action="store_true", help="AST Code Skeleton extraction.")

def handle_scan(args: argparse.Namespace) -> None:
    no_color_flag: bool = False
    if hasattr(args, 'no_color') is True:
        if getattr(args, 'no_color') is True:
            no_color_flag = True
            
    terminal.configure_environment(no_color=no_color_flag)
    
    verbose_flag: bool = False
    if hasattr(args, 'verbose') is True:
        if getattr(args, 'verbose') is True:
            verbose_flag = True
            
    quiet_flag: bool = False
    if hasattr(args, 'quiet') is True:
        if getattr(args, 'quiet') is True:
            quiet_flag = True
            
    logger.configure(verbose=verbose_flag, quiet=quiet_flag)
    
    if len(sys.argv) == 1:
        terminal.display_banner()
        sys.exit(0)

    try:
        target_path: Path = Path(args.target).resolve(strict=True)
        if target_path.is_dir() is False:
            raise ConfigurationError(
                message=f"Target path '{args.target}' is not a valid directory.",
                hint="Please provide a valid folder path to scan."
            )

        excludes: List[str] = []
        is_explicit_ignore: bool = False
        
        if args.exclude is not None:
            if len(args.exclude) > 0:
                excludes = expand_scan_excludes(args.exclude)
                for raw_input in args.exclude:
                    if "ignore" in raw_input.lower():
                        is_explicit_ignore = True
                        break

        is_search_mode: bool = False
        if args.find is not None:
            if len(args.find) > 0:
                is_search_mode = True
                
        is_full_mode: bool = False
        if args.full is True:
            is_full_mode = True
            
        is_search_only: bool = False
        if is_search_mode is True:
            if is_full_mode is False:
                is_search_only = True

        is_no_hidden: bool = False
        if hasattr(args, 'no_hidden') is True:
            if getattr(args, 'no_hidden') is True:
                is_no_hidden = True
                
        file_type_arg: Optional[str] = None
        if hasattr(args, 'type') is True:
            file_type_arg = getattr(args, 'type')

        excludes = intercept_garbage_files(
            target_path=target_path, 
            current_excludes=excludes, 
            is_no_hidden=is_no_hidden, 
            is_explicit_ignore=is_explicit_ignore,
            file_type=file_type_arg,
            is_search_only=is_search_only
        )
        
        grep_pattern: Optional[str] = None
        if hasattr(args, 'grep_pattern') is True:
            grep_pattern = getattr(args, 'grep_pattern')
            
        needs_content: bool = False
        if args.full is True:
            needs_content = True
        else:
            if grep_pattern is not None:
                needs_content = True
            else:
                if args.analyze is True:
                    needs_content = True
                else:
                    if args.skeleton is True:
                        needs_content = True
        
        final_show_hidden: bool = True
        if is_no_hidden is True:
            final_show_hidden = False
        else:
            if args.find is not None:
                if len(args.find) > 0:
                    if args.find.startswith('.') is True:
                        final_show_hidden = True

        includes_arg: List[str] = []
        if hasattr(args, 'include') is True:
            if args.include is not None:
                includes_arg = getattr(args, 'include')
                
        text_only_arg: bool = False
        if args.text_only is True:
            text_only_arg = True
        else:
            if grep_pattern is not None:
                text_only_arg = True
                
        use_regex_arg: bool = False
        if hasattr(args, 'regex') is True:
            if getattr(args, 'regex') is True:
                use_regex_arg = True

        template_path_arg: Optional[Path] = None
        if hasattr(args, 'template') is True:
            if getattr(args, 'template') is not None:
                template_path_arg = Path(getattr(args, 'template')).resolve()

        config = ScanConfig(
            max_depth=args.depth,
            show_hidden=final_show_hidden,
            excludes=excludes,
            includes=includes_arg,
            file_type=file_type_arg,
            text_only=text_only_arg,
            quiet=quiet_flag,
            use_regex=use_regex_arg,
            ignore_case=args.ignore_case,
            template_path=template_path_arg
        )

        if quiet_flag is False:
            logger.info(f"Scanning directory topology in '{target_path.name}'...")

        traverser = DepthFirstTraverser()
        result: TraversalResult = traverser.traverse(target_path, config, collect_content=needs_content)

        if quiet_flag is False:
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

        if args.analyze is True:
            orchestrator.add_plugin(AnalyzerPlugin())
            if args.full is True:
                orchestrator.add_plugin(ContextInjectorPlugin())
            
        if grep_pattern is not None:
            orchestrator.add_plugin(
                GrepPlugin(
                    pattern=grep_pattern, 
                    context_lines=args.context, 
                    ignore_case=args.ignore_case, 
                    format_type=args.format
                )
            )
            
        if args.skeleton is True:
            orchestrator.add_plugin(SkeletonPlugin())
            
        if args.find is not None:
            if len(args.find) > 0:
                orchestrator.add_plugin(
                    SearchPlugin(
                        keyword=args.find, 
                        delete_mode=args.delete, 
                        dry_run=args.dry_run
                    )
                )

        out_dir: Path = Path.cwd()
        if args.outdir is not None:
            out_dir = Path(args.outdir).resolve()
            
        if out_dir.exists() is False:
            out_dir.mkdir(parents=True, exist_ok=True)
        
        out_file: Path
        if args.name is not None:
            out_file = out_dir / args.name
        else:
            ext_map: Dict[str, str] = {'md': '.md', 'txt': '.txt', 'image': '.png', 'json': '.json', 'xml': '.xml'}
            suffix: str = '.md'
            if args.format in ext_map:
                suffix = ext_map[args.format]

            modifier: str = ""
            if args.analyze is True:
                modifier = "_analysis"
                suffix = ".md"
            elif args.skeleton is True:
                modifier = "_skeleton"
                suffix = ".md"
            elif grep_pattern is not None:
                modifier = "_grep"
            elif args.find is not None:
                if len(args.find) > 0:
                    modifier = f"_search_{args.find}"
                
            out_file = out_dir / f"{target_path.name}{modifier}{suffix}"

        orchestrator.run_pipeline(target_path, config, result, out_file=out_file, is_full=args.full)

    except SeedlingToolsError as err:
        logger.error(str(err))
        sys.exit(err.exit_code)
    except KeyboardInterrupt:
        logger.info("\nOperation interrupted by user.")
        sys.exit(0)