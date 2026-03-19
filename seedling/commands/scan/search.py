import sys
import shutil 
from pathlib import Path
from seedling.core.ui import ask_yes_no
from seedling.core.logger import logger
from seedling.core.filesystem import search_items, scan_dir_lines, is_text_file, safe_read_text

def run_search(args, target_path):
    # 执行搜索
    exact, fuzzy = search_items(target_path, args.find, args.show_hidden, args.exclude, args.text_only, args.quiet)
    all_matches = exact + fuzzy
    
    def format_item(item):
        prefix = "[DIR] 📁" if item.is_dir() else "📄"
        rel = item.relative_to(target_path) if target_path in item.parents else item
        return f"{prefix} {rel}"

    # 终端打印结果
    if exact:
        logger.info(f"\n🎯 Exact matches for '{args.find}':")
        for item in exact[:20]: logger.info(f"  {format_item(item)}")
    else:
        logger.info(f"\n❓ No exact matches found for '{args.find}'.")

    if fuzzy:
        logger.info(f"\n💡 Did you mean one of these? (Fuzzy matches):")
        for item in fuzzy[:10]: logger.info(f"  {format_item(item)}")

    if not all_matches:
        logger.error("No matches found. Aborting.")
        return

    # 危险删除操作逻辑 (--delete)
    if args.delete:
        if not sys.stdin.isatty():
            logger.error("Dangerous operation '--delete' can only be used in an interactive terminal.")
            return

        if fuzzy:
            logger.warning(f"\n⚠️  Fuzzy matches may include unintended items!")
            logger.info("Fuzzy matches staged for deletion:")
            for item in fuzzy:
                logger.info(f"  - {item.relative_to(target_path)}")
                
            if not ask_yes_no("👉 Do you want to INCLUDE these fuzzy matches in the deletion? [y/n]: "):
                logger.info("✅ Fuzzy matches removed from the deletion queue.")
                fuzzy = []
                all_matches = exact  
                
        if not all_matches:
            logger.info("\n⏭️ No items left to delete. Aborting.")
            return
        
        logger.warning(f"\nCRITICAL WARNING: You are about to PERMANENTLY DELETE {len(all_matches)} items.")
        confirm = input(f"👉 Please type 'CONFIRM DELETE' to proceed: ").strip()
        
        if confirm == "CONFIRM DELETE":
            deleted_count = 0
            for item in all_matches:
                if item.is_symlink():
                    try:
                        item.unlink()
                        deleted_count += 1
                        logger.info(f" 🗑️ Deleted (Symlink): {item.relative_to(target_path)}")
                    except Exception as e:
                        logger.error(f" Failed to delete symlink {item.relative_to(target_path)}: {e}")
                    continue
                if not item.exists():
                    continue
                try:
                    if item.is_dir():
                        shutil.rmtree(item)
                    else:
                        item.unlink()
                    deleted_count += 1
                    logger.info(f" 🗑️ Deleted: {item.relative_to(target_path)}")
                except Exception as e:
                    logger.error(f" Failed to delete {item.relative_to(target_path)}: {e}")
            logger.info(f"\n✅ Successfully deleted {deleted_count} items. Operation complete.")
            return

    # 默认情况下，仅输出到 CLI，直接退出
    if not args.full:
        logger.info("\n✅ Search complete! (Tip: Use '--full' to generate a report file with full source code context)")
        return

    # 强制生成包含“目录高亮”和“全部源码”的文件
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
        
    # 生成高亮的树状图
    highlights = set(all_matches)
    stats = {"dirs": 0, "files": 0}
    lines = scan_dir_lines(
        target_path, 
        max_depth=args.depth, 
        show_hidden=args.show_hidden, 
        excludes=args.exclude, 
        stats=stats, 
        highlights=highlights, 
        text_only=args.text_only,
        quiet=args.quiet
    )
    
    if not args.quiet:
        sys.stdout.write(f"\r✅ Tree generation complete!                      \n")
    
    tree_text = f"{target_path.name}/\n" + "\n".join(lines)

    # 写入最终的 Markdown 报告
    try:
        with open(final_search_file, 'w', encoding='utf-8') as f:
            f.write(f"# Search Results for '{args.find}' in `{target_path}`\n\n")
            
            f.write("============================================================\n")
            f.write("📁 MATCHED SOURCE FILES (SUMMARY)\n")
            f.write("============================================================\n\n")
            for m in exact: f.write(f"- 🎯 [EXACT] {m.relative_to(target_path)}\n")
            for m in fuzzy: f.write(f"- 💡 [FUZZY] {m.relative_to(target_path)}\n")
            
            f.write("\n\n============================================================\n")
            f.write("🌲 PROJECT TREE (WITH HIGHLIGHTS)\n")
            f.write("============================================================\n\n")
            f.write(f"```text\n{tree_text}\n```\n\n")
            
            f.write("============================================================\n")
            f.write("📁 MATCHED SOURCE FILES (FULL CONTEXT)\n")
            f.write("============================================================\n\n")
            
            extracted_files = 0
            for m in all_matches:
                if m.is_file() and is_text_file(m):
                    content = safe_read_text(m, quiet=True)
                    if content is not None:
                        extracted_files += 1
                        f.write(f"### FILE: {m.relative_to(target_path)}\n")
                        lang = m.suffix.lstrip('.')
                        
                        max_ticks = 2
                        for line in content.split('\n'):
                            stripped = line.strip()
                            if stripped.startswith('`'):
                                ticks = len(stripped) - len(stripped.lstrip('`'))
                                if ticks > max_ticks:
                                    max_ticks = ticks
                        fence = '`' * (max_ticks + 1)
                        
                        f.write(f"{fence}{lang}\n{content}\n{fence}\n\n")
                        
        logger.info(f"\n✅ Full results ({extracted_files} files with code) saved to:\n   👉 {final_search_file}\n")
    except Exception as e:
        logger.error(f"Failed to save search results: {e}")