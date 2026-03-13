import re
from pathlib import Path
from seedling.core.ui import ask_yes_no
from seedling.core.io import extract_tree_block, extract_file_contents

def build_structure_from_file(source_file, target_dir, check_mode=False, force_mode=False):
    tree_lines = extract_tree_block(source_file)
    file_contents = extract_file_contents(source_file)

    if not tree_lines and not file_contents:
        print(f"\n👻 ERROR: Could not find any valid tree structure or file contents in '{source_file}'.")
        return False

    target_path = Path(target_dir).resolve()
    parsed_items = []
    
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
        if clean_name: parsed_items.append({'depth': depth, 'name': clean_name, 'is_dir': is_dir})
             
    for i, item in enumerate(parsed_items):
        if i + 1 < len(parsed_items):
            if parsed_items[i+1]['depth'] > item['depth']:
                item['is_dir'] = True

    if parsed_items and parsed_items[0]['depth'] == 0:
        if not any(item['depth'] == 0 for item in parsed_items[1:]):
            parsed_items.pop(0)

    if check_mode:
        print(f"\n🔍 [CHECK MODE] Simulating build in: {target_path}")
        missing, existing = set(), set()
        stack = [(-1, target_path)]
        
        for item in parsed_items:
            while stack and stack[-1][0] >= item['depth']: stack.pop()
            current_path = stack[-1][1] / item['name']
            if item['is_dir']: stack.append((item['depth'], current_path))
            if current_path.exists(): existing.add(current_path)
            else: missing.add(current_path)
        
        for rel_path in file_contents.keys():
            p = target_path / rel_path
            if p.exists(): existing.add(p)
            else: missing.add(p)
            
        print(f"   - 🟢 Already Exists: {len(existing)} items")
        print(f"   - 🔴 Missing (Will create): {len(missing)} items")
        
        if missing:
            if not ask_yes_no("\n👉 Proceed to build the missing items? [y/n]: "):
                print("Aborted.")
                return False
        else:
            print("✅ Everything is already perfectly built!")
            return True

    print(f"\n🏗️  Building structure in: {target_path} ...\n")
    if file_contents:
        print(f"📦 Discovered source code for {len(file_contents)} files! Restoring magic...\n")

    stack = [(-1, target_path)]
    dirs_created, files_created, skipped = 0, 0, 0
    populated_count = 0
    handled_files = set()
    
    for item in parsed_items:
        depth = item['depth']
        name = item['name']

        while stack and stack[-1][0] >= depth: stack.pop()
        current_path = stack[-1][1] / name
        rel_path = current_path.relative_to(target_path)
        posix_rel = rel_path.as_posix()
        handled_files.add(posix_rel)
        
        try:
            if item['is_dir']:
                if current_path.exists():
                    print(f" ⏭️  Skipped (Exists): 📁 {rel_path}")
                    skipped += 1
                else:
                    current_path.mkdir(parents=True, exist_ok=True)
                    print(f" ✨ Created:          📁 {rel_path}")
                    dirs_created += 1
                stack.append((depth, current_path))
            else:
                current_path.parent.mkdir(parents=True, exist_ok=True)
                if current_path.exists() and not force_mode:
                    print(f" ⏭️  Skipped (Exists): 📄 {rel_path}")
                    skipped += 1
                else:
                    is_overwrite = current_path.exists()
                    content_to_write = file_contents.get(posix_rel, "")
                    
                    with open(current_path, 'w', encoding='utf-8') as f: 
                        f.write(content_to_write)
                        
                    if content_to_write:
                        populated_count += 1
                        if is_overwrite: print(f" ⚠️  Overwritten+Data: 📄 {rel_path}")
                        else: print(f" 🪄 Restored Data:    📄 {rel_path}")
                    else:
                        if is_overwrite: print(f" ⚠️  Overwritten:      📄 {rel_path}")
                        else: print(f" ✨ Created Empty:    📄 {rel_path}")
                    files_created += 1
        except Exception as e:
            print(f" ❌ Failed to create '{name}': {e}")

    for posix_rel, content in file_contents.items():
        if posix_rel not in handled_files:
            current_path = target_path / posix_rel
            try:
                current_path.parent.mkdir(parents=True, exist_ok=True)
                if current_path.exists() and not force_mode:
                    print(f" ⏭️  Skipped (Exists): 📄 {posix_rel} (from source block)")
                    skipped += 1
                else:
                    is_overwrite = current_path.exists()
                    with open(current_path, 'w', encoding='utf-8') as f:
                        f.write(content)
                    populated_count += 1
                    files_created += 1
                    if is_overwrite: print(f" ⚠️  Overwritten+Data: 📄 {posix_rel} (from source block)")
                    else: print(f" 🪄 Restored Data:    📄 {posix_rel} (from source block)")
            except Exception as e:
                print(f" ❌ Failed to restore '{posix_rel}': {e}")
            
    summary_parts = [
        f"📁 {dirs_created} dirs",
        f"📄 {files_created} files ({populated_count} w/ code)",
        f"⏭️  {skipped} skipped"
    ]
    print(f"\n✅ Build Complete! [ {' | '.join(summary_parts)} ]\n")
    return True