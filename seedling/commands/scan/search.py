import sys
import shutil
import difflib
import re
from pathlib import Path
from typing import List, Tuple
from seedling.core.ui import ask_yes_no
from seedling.core.logger import logger
from seedling.core.config import ScanConfig
from seedling.core.traversal import TraversalResult, build_tree_lines
from seedling.core.io import get_dynamic_fence, check_overwrite_safely

def run_search(args, target_path: Path, config: ScanConfig, result: TraversalResult):
    """搜索命令的控制入口"""
    keyword = args.find
    exact_matches: List[Path] = []               # 匹配路径
    fuzzy_candidates: List[Tuple[str, Path]] = [] # 模糊匹配候选

    regex_pattern = None
    if config.use_regex:
        try:
            regex_pattern = re.compile(keyword, re.IGNORECASE)
        except re.error as e:
            logger.error(f"Invalid regex pattern: {e}")
            return

    keyword_lower = "" if config.use_regex else keyword.lower()

    for item in result.items:
        if item.is_dir: continue
        name = item.path.name

        if config.use_regex and regex_pattern:
            matched = bool(regex_pattern.search(name))
        else:
            matched = keyword_lower in name.lower()
        
        if matched: 
            exact_matches.append(item.path)
        else: 
            fuzzy_candidates.append((name, item.path))

    fuzzy_matches = []
    # 高复杂度模糊字符串匹配
    if not config.use_regex and fuzzy_candidates:
        unique_names = list(set(n for n, p in fuzzy_candidates))
        close_names = difflib.get_close_matches(keyword, unique_names, n=10, cutoff=0.7)
        fuzzy_matches = [p for n, p in fuzzy_candidates if n in close_names]

    all_matches = exact_matches + fuzzy_matches

    if args.delete and not sys.stdin.isatty():
        logger.error("Dangerous operation '--delete' can only be used in an interactive terminal.")
        return

    def format_item(item):
        """路径格式化工具"""
        prefix = "[DIR] 📁" if item.is_dir() else "📄"
        try: rel = item.relative_to(target_path)
        except ValueError: rel = item
        return f"{prefix} {rel}"

    if exact_matches:
        logger.info(f"\n🎯 Exact matches for '{keyword}':")
        for item in exact_matches[:20]: logger.info(f"  {format_item(item)}")
    else:
        logger.info(f"\n❓ No exact matches found for '{keyword}'.")

    if fuzzy_matches:
        logger.info(f"\n💡 Did you mean one of these? (Fuzzy matches):")
        for item in fuzzy_matches[:10]: logger.info(f"  {format_item(item)}")

    if not all_matches:
        logger.error("No matches found. Aborting.")
        return

    # 删除操作
    if args.delete:
        dry_run = getattr(args, 'dry_run', False)
        if fuzzy_matches:
            logger.warning("\nFuzzy matches may include unintended items!")
            if not ask_yes_no("Do you want to INCLUDE these fuzzy matches in the deletion? [y/n]: "):
                fuzzy_matches = []
                all_matches = exact_matches
                
        if not all_matches:
            logger.info("\nNo items left to delete. Aborting."); return

        logger.warning(f"\n{'[DRY-RUN] ' if dry_run else ''}Items to be deleted ({len(all_matches)} total):")
        for item in all_matches:
            try: rel = item.relative_to(target_path)
            except ValueError: rel = item
            logger.info(f"  {'[DIR]' if item.is_dir() else '[FILE]'} {rel}")

        if dry_run:
            logger.info(f"\n[DRY-RUN] Preview complete. No files were deleted."); return

        confirm = input(f"Please type 'CONFIRM DELETE' to proceed: ").strip()
        if confirm == "CONFIRM DELETE":
            deleted_count = 0
            for item in all_matches:
                try:
                    if item.is_symlink() or item.is_file(): item.unlink()
                    else: shutil.rmtree(item)
                    deleted_count += 1
                except Exception as e:
                    logger.error(f" Failed to delete {item}: {e}")
            logger.info(f"\nSuccessfully deleted {deleted_count} items.")
            return

    if not args.full:
        logger.info("\n✅ Search complete! (Tip: Use '--full' to generate a report file with full source code context)")
        return

    logger.info("\n🚀 Power Mode triggered! Generating search report with full source code...")
    out_dir = Path(args.outdir).resolve() if args.outdir else Path.cwd()
    final_search_file = out_dir / (args.name or f"{target_path.name or 'root'}_search_{keyword}.md")

    if not check_overwrite_safely(final_search_file): 
        return

    config.highlights = set(all_matches)
    lines = build_tree_lines(result, config, root_path=target_path)
    tree_text = f"{target_path.name}/\n" + "\n".join(lines)

    try:
        with open(final_search_file, 'w', encoding='utf-8') as f:
            f.write(f"# Search Results for '{keyword}' in `{target_path}`\n\n")
            f.write("============================================================\n📁 MATCHED SOURCE FILES (SUMMARY)\n============================================================\n\n")
            for m in exact_matches: f.write(f"- 🎯 [EXACT] {m.relative_to(target_path)}\n")
            for m in fuzzy_matches: f.write(f"- 💡 [FUZZY] {m.relative_to(target_path)}\n")
            f.write(f"\n\n============================================================\n🌲 PROJECT TREE (WITH HIGHLIGHTS)\n============================================================\n\n```text\n{tree_text}\n```\n\n")
            f.write("============================================================\n📁 MATCHED SOURCE FILES (FULL CONTEXT)\n============================================================\n\n")

            extracted_files = 0
            for m in all_matches:
                if m.is_dir(): 
                    continue
                for item in result.text_files:
                    if item.path == m:
                        content = result.get_content(item, quiet=True)
                        if content:
                            extracted_files += 1
                            f.write(f"### FILE: {m.relative_to(target_path)}\n")
                            lang = m.suffix.lstrip('.')
                            fence = get_dynamic_fence(content)
                            f.write(f"{fence}{lang}\n{content}\n{fence}\n\n")
                        break
                        
        logger.info(f"\n✅ Full results ({extracted_files} files with code) saved to:\n   👉 {final_search_file}\n")
    except Exception as e:
        logger.error(f"Failed to save search results: {e}")
