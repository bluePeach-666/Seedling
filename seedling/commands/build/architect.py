import re
import sys
from pathlib import Path
from seedling.core.ui import ask_yes_no
from seedling.core.io import extract_tree_block, extract_file_contents
from seedling.core.logger import logger

def is_safe_path(path, target):
    if sys.version_info >= (3, 9):
        return path.is_relative_to(target)
    else:
        try:
            path.relative_to(target)
            return True
        except ValueError:
            return False

def build_structure_from_file(source_file, target_dir, check_mode=False, force_mode=False):
    tree_lines = extract_tree_block(source_file)
    file_contents = extract_file_contents(source_file)

    if not tree_lines and not file_contents:
        logger.error(f"👻 Could not find any valid tree structure or file contents in '{source_file}'.")
        return False

    target_path = Path(target_dir).resolve()
    
    # ==========================================
    # Safe Parsing Phase
    # ==========================================
    raw_parsed_items = []
    for line in tree_lines:
        match = re.match(r'^([│├└─\s]*)(.+)$', line)
        if not match: continue
            
        prefix, content = match.groups()
        depth = len(prefix) 
        
        clean_name = content.split('<-')[0].strip()
        clean_name = re.split(r'\s{2,}#', clean_name)[0].strip()
        clean_name = re.split(r'\s{2,}', clean_name)[0].strip() 
        
        is_dir = clean_name.endswith('/')
        if is_dir: clean_name = clean_name.rstrip('/')
            
        if clean_name and clean_name not in ['.', '..']: 
            raw_parsed_items.append({'depth': depth, 'name': clean_name, 'is_dir': is_dir})
             
    for i, item in enumerate(raw_parsed_items):
        if i + 1 < len(raw_parsed_items):
            if raw_parsed_items[i+1]['depth'] > item['depth']:
                item['is_dir'] = True

    if raw_parsed_items and raw_parsed_items[0]['depth'] == 0:
        if not any(item['depth'] == 0 for item in raw_parsed_items[1:]):
            raw_parsed_items.pop(0)

    parsed_items = []
    stack = [(-1, target_path)]
    for item in raw_parsed_items:
        while stack and stack[-1][0] >= item['depth']: 
            stack.pop()
        
        current_path = (stack[-1][1] / item['name']).resolve()
        if not is_safe_path(current_path, target_path):
            logger.warning(f"🚫 Blocked (Security): {item['name']} (Attempted path traversal)")
            continue

        item['safe_path'] = current_path
        parsed_items.append(item)
        
        if item['is_dir']: 
            stack.append((item['depth'], current_path))
            
    safe_file_contents = {}
    for rel_path, content in file_contents.items():
        p = (target_path / rel_path).resolve()
        if not is_safe_path(p, target_path):
            logger.warning(f"🚫 Blocked (Security): {rel_path} (Attempted path traversal in code block)")
            continue
        safe_file_contents[rel_path] = (p, content)

    # ==========================================
    # Dry Run
    # ==========================================
    if check_mode:
        logger.info(f"\n🔍 [CHECK MODE] Simulating build in: {target_path}")
        missing, existing = set(), set()
        
        for item in parsed_items:
            if item['safe_path'].exists(): existing.add(item['safe_path'])
            else: missing.add(item['safe_path'])
            
        for rel_path, (p, content) in safe_file_contents.items():
            if p.exists(): existing.add(p)
            else: missing.add(p)
            
        logger.info(f"   - 🟢 Already Exists: {len(existing)} items")
        logger.info(f"   - 🔴 Missing (Will create): {len(missing)} items")
        
        if missing:
            if not ask_yes_no("\n👉 Proceed to build the missing items? [y/n]: "):
                logger.info("Aborted.")
                return False
        else:
            logger.info("✅ Everything is already perfectly built!")
            return True

    # ==========================================
    # Build Phase
    # ==========================================
    logger.info(f"\n🏗️  Building structure in: {target_path} ...\n")
    if safe_file_contents:
        logger.info(f"📦 Discovered source code for {len(safe_file_contents)} files! Restoring magic...\n")

    dirs_created, files_created, skipped = 0, 0, 0
    populated_count = 0
    handled_files = set()
    
    for item in parsed_items:
        current_path = item['safe_path']
        rel_path = current_path.relative_to(target_path)
        posix_rel = rel_path.as_posix()
        handled_files.add(posix_rel)
        
        try:
            if item['is_dir']:
                if current_path.exists():
                    logger.info(f" ⏭️  Skipped (Exists): 📁 {rel_path}")
                    skipped += 1
                else:
                    current_path.mkdir(parents=True, exist_ok=True)
                    logger.info(f" ✨ Created:         📁 {rel_path}")
                    dirs_created += 1
            else:
                current_path.parent.mkdir(parents=True, exist_ok=True)
                if current_path.exists() and not force_mode:
                    logger.info(f" ⏭️  Skipped (Exists): 📄 {rel_path}")
                    skipped += 1
                else:
                    is_overwrite = current_path.exists()
                    content_to_write = safe_file_contents[posix_rel][1] if posix_rel in safe_file_contents else ""
                    
                    with open(current_path, 'w', encoding='utf-8') as f: 
                        f.write(content_to_write)
                        
                    if content_to_write:
                        populated_count += 1
                        if is_overwrite: logger.warning(f" ⚠️  Overwritten+Data: 📄 {rel_path}")
                        else: logger.info(f" 🪄 Restored Data:    📄 {rel_path}")
                    else:
                        if is_overwrite: logger.warning(f" ⚠️  Overwritten:      📄 {rel_path}")
                        else: logger.info(f" ✨ Created Empty:    📄 {rel_path}")
                    files_created += 1
        except Exception as e:
            logger.error(f" Failed to create '{item['name']}': {e}")

    for posix_rel, (current_path, content) in safe_file_contents.items():
        if posix_rel not in handled_files:
            try:
                current_path.parent.mkdir(parents=True, exist_ok=True)
                if current_path.exists() and not force_mode:
                    logger.info(f" ⏭️  Skipped (Exists): 📄 {posix_rel} (from source block)")
                    skipped += 1
                else:
                    is_overwrite = current_path.exists()
                    with open(current_path, 'w', encoding='utf-8') as f:
                        f.write(content)
                    populated_count += 1
                    files_created += 1
                    if is_overwrite: logger.warning(f" ⚠️  Overwritten+Data: 📄 {posix_rel} (from source block)")
                    else: logger.info(f" 🪄 Restored Data:    📄 {posix_rel} (from source block)")
            except Exception as e:
                logger.error(f" Failed to restore '{posix_rel}': {e}")
            
    summary_parts = [
        f"📁 {dirs_created} dirs",
        f"📄 {files_created} files ({populated_count} w/ code)",
        f"⏭️  {skipped} skipped"
    ]
    logger.info(f"\n✅ Build Complete! [ {' | '.join(summary_parts)} ]\n")
    return True