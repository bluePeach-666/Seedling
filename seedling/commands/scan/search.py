import sys
import shutil
import difflib
import re
from pathlib import Path
from typing import List, Tuple

from seedling.core.ui import ask_yes_no
from seedling.core.logger import logger
from seedling.core.config import ScanConfig
from seedling.core.detection import is_text_file
from seedling.core.patterns import is_valid_item
from seedling.core.traversal import traverse_directory, TraversalItem, build_tree_lines
from seedling.core.filesystem import safe_read_text
from seedling.core.io import get_dynamic_fence


def run_search(args, target_path: Path):
    """Execute search logic and generate Markdown report in Power Mode."""

    # Build initial configuration
    config = ScanConfig(
        show_hidden=args.show_hidden,
        excludes=args.exclude,
        includes=getattr(args, 'include', []),
        file_type=getattr(args, 'type', None),
        text_only=args.text_only,
        quiet=args.quiet,
        use_regex=getattr(args, 'regex', False)
    )

    keyword = args.find

    # Use unified traversal for single-pass scanning
    # Collect content eagerly if --full is enabled (optimization)
    result = traverse_directory(
        target_path,
        config,
        collect_content=args.full
    )

    # Filter matches in-memory (no re-traversal)
    exact_matches: List[Path] = []
    fuzzy_candidates: List[Tuple[str, Path]] = []

    regex_pattern = None
    if config.use_regex:
        try:
            regex_pattern = re.compile(keyword, re.IGNORECASE)
        except re.error as e:
            logger.error(f"Invalid regex pattern: {e}")
            return

    keyword_lower = keyword.lower() if not config.use_regex else None

    for item in result.items:
        if item.is_dir:
            continue

        name = item.path.name
        matched = False

        if config.use_regex and regex_pattern:
            matched = bool(regex_pattern.search(name))
        else:
            matched = keyword_lower in name.lower()

        if matched:
            exact_matches.append(item.path)
        else:
            fuzzy_candidates.append((name, item.path))

    # Fuzzy matching (skip for regex mode)
    fuzzy_matches = []
    if not config.use_regex and fuzzy_candidates:
        unique_names = list(set(n for n, p in fuzzy_candidates))
        close_names = difflib.get_close_matches(keyword, unique_names, n=10, cutoff=0.7)
        fuzzy_matches = [p for n, p in fuzzy_candidates if n in close_names]

    all_matches = exact_matches + fuzzy_matches

    if args.delete:
        if not sys.stdin.isatty():
            logger.error("Dangerous operation '--delete' can only be used in an interactive terminal.")
            return

    def format_item(item):
        prefix = "[DIR] 📁" if item.is_dir() else "📄"
        try:
            rel = item.relative_to(target_path)
        except ValueError:
            rel = item
        return f"{prefix} {rel}"

    # Print terminal results
    if exact_matches:
        logger.info(f"\n🎯 Exact matches for '{args.find}':")
        for item in exact_matches[:20]:
            logger.info(f"  {format_item(item)}")
    else:
        logger.info(f"\n❓ No exact matches found for '{args.find}'.")

    if fuzzy_matches:
        logger.info(f"\n💡 Did you mean one of these? (Fuzzy matches):")
        for item in fuzzy_matches[:10]:
            logger.info(f"  {format_item(item)}")

    if not all_matches:
        logger.error("No matches found. Aborting.")
        return

    # Dangerous delete operation logic (--delete)
    if args.delete:
        dry_run = getattr(args, 'dry_run', False)

        if fuzzy_matches:
            logger.warning("\nFuzzy matches may include unintended items!")
            logger.info("Fuzzy matches staged for deletion:")
            for item in fuzzy_matches:
                logger.info(f"  - {item.relative_to(target_path)}")

            if not ask_yes_no("Do you want to INCLUDE these fuzzy matches in the deletion? [y/n]: "):
                logger.info("Fuzzy matches removed from the deletion queue.")
                fuzzy_matches = []
                all_matches = exact_matches

        if not all_matches:
            logger.info("\nNo items left to delete. Aborting.")
            return

        # Display preview of items to be deleted
        logger.warning(f"\n{'[DRY-RUN] ' if dry_run else ''}Items to be deleted ({len(all_matches)} total):")
        logger.info("=" * 50)
        for item in all_matches:
            item_type = "[DIR]" if item.is_dir() else "[FILE]"
            try:
                rel = item.relative_to(target_path)
            except ValueError:
                rel = item
            logger.info(f"  {item_type} {rel}")
        logger.info("=" * 50)

        # If dry-run mode, exit after showing preview
        if dry_run:
            logger.info(f"\n[DRY-RUN] Preview complete. No files were deleted.")
            logger.info("Remove --dry-run flag to execute deletion.")
            return

        logger.warning(f"\nCRITICAL WARNING: You are about to PERMANENTLY DELETE {len(all_matches)} items.")
        confirm = input(f"Please type 'CONFIRM DELETE' to proceed: ").strip()

        if confirm == "CONFIRM DELETE":
            deleted_count = 0
            for item in all_matches:
                try:
                    if item.is_symlink():
                        item.unlink()
                        logger.info(f" Deleted (Symlink): {item.relative_to(target_path)}")
                    elif item.is_dir():
                        shutil.rmtree(item)
                        logger.info(f" Deleted (Dir): {item.relative_to(target_path)}")
                    else:
                        item.unlink()
                        logger.info(f" Deleted (File): {item.relative_to(target_path)}")
                    deleted_count += 1
                except Exception as e:
                    logger.error(f" Failed to delete {item}: {e}")
            logger.info(f"\nSuccessfully deleted {deleted_count} items. Operation complete.")
            return

    # If --full is not enabled, don't generate file
    if not args.full:
        logger.info("\n✅ Search complete! (Tip: Use '--full' to generate a report file with full source code context)")
        return

    # Generate report with highlighted tree and source code content
    logger.info("\n🚀 Power Mode triggered! Generating search report with full source code...")

    out_dir = Path(args.outdir).resolve() if args.outdir else Path.cwd()
    target_name = target_path.name or "root"
    search_filename = args.name or f"{target_name}_search_{args.find}.md"
    final_search_file = out_dir / search_filename

    if final_search_file.exists():
        logger.warning(f"NOTICE: Search report already exists:\n   👉 {final_search_file}")
        if not ask_yes_no("Do you want to overwrite it? [y/n]: "):
            logger.info("Aborted. No report was generated.")
            return

    # Generate tree with highlights (use cached traversal result)
    config.highlights = set(all_matches)

    # Use build_tree_lines from cached result (no re-traversal!)
    lines = build_tree_lines(result, config, root_path=target_path)

    if not args.quiet:
        sys.stdout.write(f"\r✅ Tree generation complete!                      \n")

    tree_text = f"{target_path.name}/\n" + "\n".join(lines)

    try:
        with open(final_search_file, 'w', encoding='utf-8') as f:
            f.write(f"# Search Results for '{args.find}' in `{target_path}`\n\n")

            # Summary section
            f.write("============================================================\n")
            f.write("📁 MATCHED SOURCE FILES (SUMMARY)\n")
            f.write("============================================================\n\n")
            for m in exact_matches:
                f.write(f"- 🎯 [EXACT] {m.relative_to(target_path)}\n")
            for m in fuzzy_matches:
                f.write(f"- 💡 [FUZZY] {m.relative_to(target_path)}\n")

            # Tree section
            f.write("\n\n============================================================\n")
            f.write("🌲 PROJECT TREE (WITH HIGHLIGHTS)\n")
            f.write("============================================================\n\n")
            f.write(f"```text\n{tree_text}\n```\n\n")

            # Source code content section
            f.write("============================================================\n")
            f.write("📁 MATCHED SOURCE FILES (FULL CONTEXT)\n")
            f.write("============================================================\n\n")

            extracted_files = 0
            for m in all_matches:
                if m.is_file() and is_text_file(m):
                    # Get content from cache (no re-reading!)
                    # Find the TraversalItem for this path
                    cached_content = None
                    for item in result.text_files:
                        if item.path == m:
                            cached_content = result.get_content(item, quiet=True)
                            break

                    # Fallback to direct read if not in cache
                    if cached_content is None:
                        cached_content = safe_read_text(m, quiet=True)

                    if cached_content is not None:
                        extracted_files += 1
                        f.write(f"### FILE: {m.relative_to(target_path)}\n")
                        lang = m.suffix.lstrip('.')

                        fence = get_dynamic_fence(cached_content)

                        f.write(f"{fence}{lang}\n{cached_content}\n{fence}\n\n")

        logger.info(f"\n✅ Full results ({extracted_files} files with code) saved to:\n   👉 {final_search_file}\n")
    except Exception as e:
        logger.error(f"Failed to save search results: {e}")
