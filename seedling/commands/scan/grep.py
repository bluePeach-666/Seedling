"""Content search module with context support."""
import re
from pathlib import Path
from typing import List, Callable
from dataclasses import dataclass
from seedling.core.config import ScanConfig
from seedling.core.filesystem import safe_read_text, is_text_file
from seedling.core.patterns import is_valid_item
from seedling.core.logger import logger


@dataclass
class GrepMatch:
    """Represents a single match found in a file."""
    file_path: Path
    relative_path: Path
    line_number: int
    line_content: str
    context_before: List[str]
    context_after: List[str]


def grep_files(
    dir_path: Path,
    pattern: str,
    config: ScanConfig,
    context: int = 0,
    ignore_case: bool = False
) -> List[GrepMatch]:
    """
    Search inside file contents for pattern matches.

    Args:
        dir_path: Target directory to search
        pattern: Search pattern (string or regex)
        config: Scan configuration
        context: Number of context lines to show around matches
        ignore_case: If True, perform case-insensitive search (default: case-sensitive)

    Returns:
        List of GrepMatch objects
    """
    matches: List[GrepMatch] = []
    base_dir = dir_path.resolve()

    # Build matcher function based on mode
    # Default is case-sensitive; use -i flag to enable case-insensitive
    regex_flags = re.IGNORECASE if ignore_case else 0

    if config.use_regex:
        try:
            compiled = re.compile(pattern, regex_flags)
            matcher: Callable[[str], bool] = lambda line: bool(compiled.search(line))
        except re.error as e:
            logger.error(f"Invalid regex pattern: {e}")
            return []
    else:
        if ignore_case:
            pattern_lower = pattern.lower()
            matcher = lambda line: pattern_lower in line.lower()
        else:
            # Case-sensitive exact match
            matcher = lambda line: pattern in line

    # DFS traversal
    stack = [dir_path]
    while stack:
        curr = stack.pop()
        try:
            for item in curr.iterdir():
                if not is_valid_item(item, base_dir, config):
                    continue

                if item.is_file() and is_text_file(item):
                    matches.extend(_grep_file(item, base_dir, matcher, context))
                elif item.is_dir() and not item.is_symlink():
                    stack.append(item)
        except PermissionError:
            pass

    return matches


def _grep_file(file_path: Path, base: Path, matcher: Callable[[str], bool], context: int) -> List[GrepMatch]:
    """Search within a single file for matches."""
    matches: List[GrepMatch] = []
    content = safe_read_text(file_path, quiet=True)
    if not content:
        return matches

    lines = content.split('\n')
    rel_path = file_path.relative_to(base)

    for i, line in enumerate(lines):
        if matcher(line):
            start = max(0, i - context)
            end = min(len(lines), i + context + 1)
            matches.append(GrepMatch(
                file_path=file_path,
                relative_path=rel_path,
                line_number=i + 1,
                line_content=line,
                context_before=lines[start:i],
                context_after=lines[i + 1:end]
            ))

    return matches


def format_grep_output(matches: List[GrepMatch], show_context: bool) -> str:
    """Format grep matches for terminal or file output."""
    lines = []
    for m in matches:
        if show_context and m.context_before:
            for i, ctx in enumerate(m.context_before):
                lines.append(f"  {m.line_number - len(m.context_before) + i}-\t{ctx}")
        lines.append(f">>> {m.relative_path}:{m.line_number}\t{m.line_content}")
        if show_context and m.context_after:
            for i, ctx in enumerate(m.context_after):
                lines.append(f"  {m.line_number + i + 1}-\t{ctx}")
    return "\n".join(lines)


def run_grep(args, target_path: Path):
    """Execute grep mode and output results."""
    from seedling.core.ui import ask_yes_no

    config = ScanConfig(
        show_hidden=args.show_hidden,
        excludes=args.exclude,
        includes=getattr(args, 'include', []),
        file_type=getattr(args, 'type', None),
        text_only=True,
        quiet=args.quiet,
        use_regex=getattr(args, 'regex', False)
    )

    # Get ignore_case from args (default: False = case-sensitive)
    ignore_case = getattr(args, 'ignore_case', False)

    case_mode = "case-insensitive" if ignore_case else "case-sensitive"
    logger.info(f"\nSearching for '{args.grep_pattern}' in {target_path} ({case_mode})...")
    matches = grep_files(target_path, args.grep_pattern, config, args.context, ignore_case)

    if not matches:
        logger.error("No matches found.")
        return

    unique_files = len(set(m.file_path for m in matches))
    logger.info(f"\nFound {len(matches)} matches in {unique_files} files:\n")
    print(format_grep_output(matches, args.context > 0))

    # Output file handling
    if args.full or args.format != 'md':
        out_dir = Path(args.outdir).resolve() if args.outdir else Path.cwd()
        out_dir.mkdir(parents=True, exist_ok=True)
        ext = '.json' if args.format == 'json' else '.md'
        out_file = out_dir / f"{target_path.name}_grep{ext}"

        if args.format == 'json':
            import json
            json_data = {
                "pattern": args.grep_pattern,
                "case_sensitive": not ignore_case,
                "target": str(target_path),
                "total_matches": len(matches),
                "files_matched": unique_files,
                "matches": [
                    {
                        "file": str(m.relative_path),
                        "line": m.line_number,
                        "content": m.line_content,
                        "context_before": m.context_before,
                        "context_after": m.context_after
                    }
                    for m in matches
                ]
            }
            with open(out_file, 'w', encoding='utf-8') as f:
                json.dump(json_data, f, indent=2, ensure_ascii=False)
        else:
            with open(out_file, 'w', encoding='utf-8') as f:
                f.write(f"# Grep Results: `{args.grep_pattern}`\n\n")
                f.write(f"**Target**: `{target_path}`\n\n")
                f.write(f"**Mode**: {'Case-insensitive' if ignore_case else 'Case-sensitive'}\n\n")
                f.write(f"**Stats**: {len(matches)} matches in {unique_files} files\n\n")
                f.write("```\n")
                f.write(format_grep_output(matches, args.context > 0))
                f.write("\n```\n")

        logger.info(f"\nResults saved to: {out_file}")
