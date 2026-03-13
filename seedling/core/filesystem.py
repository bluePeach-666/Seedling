import sys
import difflib
from pathlib import Path
from .ui import print_progress_bar

def is_text_file(file_path):
    text_extensions = {
        '.py', '.js', '.ts', '.c', '.cpp', '.h', '.java', '.go', '.rs',
        '.html', '.css', '.md', '.txt', '.json', '.yaml', '.yml', '.toml',
        '.xml', '.sh', '.bat', '.ps1', '.sql', '.ini', '.cfg', '.csv'  # <--- 新增了 .csv
    }
    return file_path.suffix.lower() in text_extensions

def scan_dir_lines(dir_path, prefix="", max_depth=None, current_depth=0, show_hidden=False, excludes=None, stats=None, highlights=None, text_only=False):
    if excludes is None: excludes = []
    if stats is None: stats = {"dirs": 0, "files": 0}
    if highlights is None: highlights = set()
        
    lines = []
    if max_depth is not None and current_depth > max_depth: return lines
    path = Path(dir_path)

    try:
        items = list(path.iterdir())
        valid_items = []
        for item in items:
            if not show_hidden and item.name.startswith('.'): continue
            if item.name in excludes: continue
            if text_only and item.is_file() and not is_text_file(item): continue # <-- 非文本文件过滤
            valid_items.append(item)
            
        valid_items.sort(key=lambda x: (not x.is_dir(), x.name.lower()))
    except PermissionError:
        lines.append(f"{prefix}└── [Permission Denied]")
        return lines
        
    for index, item in enumerate(valid_items):
        is_last = index == (len(valid_items) - 1)
        connector = "└── " if is_last else "├── "
        symlink_mark = " (symlink)" if item.is_symlink() else ""
        match_mark = " 🎯 [MATCHED]" if item in highlights else ""
        
        display_name = f"{item.name}/" if item.is_dir() else item.name
        
        lines.append(f"{prefix}{connector}{display_name}{symlink_mark}{match_mark}")
        
        if item.is_dir():
            stats["dirs"] += 1
            if not item.is_symlink():
                extension = "    " if is_last else "│   "
                lines.extend(scan_dir_lines(
                    item, prefix=prefix + extension, max_depth=max_depth, 
                    current_depth=current_depth + 1, show_hidden=show_hidden,
                    excludes=excludes, stats=stats, highlights=highlights, text_only=text_only
                ))
        else:
            stats["files"] += 1
            
        total_scanned = stats["dirs"] + stats["files"]
        if total_scanned % 15 == 0:
            print_progress_bar(total_scanned, label="Scanning", icon="⏳")
            
    return lines

def search_items(dir_path, keyword, show_hidden=False, excludes=None, text_only=False):
    if excludes is None: excludes = []
        
    exact_matches = []
    all_names = {} 
    keyword_lower = keyword.lower()
    scan_stats = {"count": 0} 
    
    def walk(current_path):
        try:
            for item in current_path.iterdir():
                if not show_hidden and item.name.startswith('.'): continue
                if item.name in excludes: continue
                if text_only and item.is_file() and not is_text_file(item): continue # <-- 搜索时的过滤
                
                scan_stats["count"] += 1
                all_names[item.name] = item
                
                if keyword_lower in item.name.lower():
                    exact_matches.append(item)
                    
                if scan_stats["count"] % 10 == 0:
                    print_progress_bar(scan_stats["count"], label="Searching", icon="🔍")
                    
                if item.is_dir() and not item.is_symlink():
                    walk(item)
        except PermissionError: pass
            
    walk(Path(dir_path))
    
    sys.stdout.write(f"\r✅ Search complete! Scanned {scan_stats['count']} items.                \n")
    sys.stdout.flush()
    
    remaining_names = [name for name in all_names.keys() if not any(ex.name == name for ex in exact_matches)]
    close_names = difflib.get_close_matches(keyword, remaining_names, n=10, cutoff=0.4)
    fuzzy_matches = [all_names[name] for name in close_names]
    
    return exact_matches, fuzzy_matches

def get_full_context(target_path, show_hidden=False, excludes=None, text_only=False, max_depth=None):
    if excludes is None: excludes = []
    context_data = []
    
    MAX_FILE_SIZE = 2 * 1024 * 1024  
    
    def walk(current_path, current_depth=0):
        if max_depth is not None and current_depth > max_depth:
            return
            
        try:
            items = sorted(list(current_path.iterdir()), key=lambda x: (not x.is_dir(), x.name.lower()))
            for item in items:
                if not show_hidden and item.name.startswith('.'): continue
                if item.name in excludes: continue
                
                if item.is_file():
                    if text_only and not is_text_file(item): continue
                    if is_text_file(item):
                        try:
                            if item.stat().st_size > MAX_FILE_SIZE:
                                continue
                            
                            sys.stdout.write(f"\r📖 Reading: {item.name[:30]:<30}... ")
                            sys.stdout.flush()
                            content = item.read_text(encoding='utf-8', errors='replace')
                            rel_path = item.relative_to(target_path)
                            context_data.append((rel_path, content))
                        except Exception: pass
                elif item.is_dir() and not item.is_symlink():
                    walk(item, current_depth + 1)
        except PermissionError: pass

    try:
        walk(target_path)
    except KeyboardInterrupt:
        sys.stdout.write("\n\n⚠️ [WARN] Read operation interrupted by user! Saving aggregated content so far...\n")
        sys.stdout.flush()
        
    return context_data