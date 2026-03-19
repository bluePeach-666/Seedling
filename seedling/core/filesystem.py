import sys
import difflib
import fnmatch
from pathlib import Path
from .ui import print_progress_bar
from .logger import logger 
from .sysinfo import get_system_mem_limit_mb, get_system_depth_limit 

MAX_FILE_SIZE = 2 * 1024 * 1024 # 2MB
MAX_ITERATION_DEPTH = 1000      # 显式深度硬上限
HARD_DEPTH_LIMIT = min(get_system_depth_limit(), MAX_ITERATION_DEPTH)

SPECIAL_TEXT_NAMES = {'makefile', 'dockerfile', 'license', 'caddyfile', 'procfile'}
TEXT_EXTENSIONS = {
    '.c', '.h', '.cpp', '.cc', '.cxx', '.c++', '.cp',         
    '.hpp', '.hxx', '.h++', '.hh', '.inc', '.inl', 
    '.cu', '.cuh',                                           
    '.py', '.js', '.ts', '.java', '.go', '.rs', '.cs',
    '.html', '.css', '.md', '.txt', 
    '.json', '.yaml', '.yml', '.toml', '.xml', 
    '.ini', '.cfg', '.csv',
    '.sh', '.bat', '.ps1', '.sql'
}

def is_text_file(file_path):
    if file_path.suffix.lower() in TEXT_EXTENSIONS: return True
    if file_path.name.lower() in SPECIAL_TEXT_NAMES: return True
    if file_path.name.startswith('.') and not file_path.suffix: return True
    return False

def is_binary_content(file_path):
    try:
        with open(file_path, 'rb') as f:
            chunk = f.read(1024)
            # Magic Numbers
            binary_signatures = [
                b'\x89PNG', b'GIF89a', b'GIF87a',  # PNG, GIF
                b'\xff\xd8\xff', b'JFIF', b'Exif', # JPEG
                b'MZ',                              # exe, dll
                b'\x7fELF',                         # so, bin
                b'PK\x03\x04',                      # ar, docx, xlsx 
                b'%PDF-',                           # PDF 
                b'Rar!\x1a\x07',                    # RAR 
                b'\x1f\x8b\x08',                    # tar.gz
            ]
            if b'\x00' in chunk or any(chunk.startswith(sig) for sig in binary_signatures):
                return True
    except Exception:
        return True 
    return False

def matches_exclude_pattern(item_path, base_dir, exclude_patterns):
    """
    检查文件/目录的相对路径是否匹配排除规则
    """
    # 生成相对于扫描根目录的路径（统一为 POSIX 格式）
    rel_path = item_path.relative_to(base_dir).as_posix()
    item_name = item_path.name
    
    for pattern in exclude_patterns:
        # 移除尾部斜杠
        clean_pattern = pattern.rstrip('/')
        
        # 文件名直接匹配
        if fnmatch.fnmatch(item_name, clean_pattern):
            return True
        # 相对路径匹配
        if fnmatch.fnmatch(rel_path, clean_pattern):
            return True
        # 递归匹配目录
        if fnmatch.fnmatch(rel_path, f"*{clean_pattern}") or fnmatch.fnmatch(rel_path, f"*/{clean_pattern}"):
            return True
        # 目录规则匹配
        if pattern.endswith('/') and item_path.is_dir() and (
            fnmatch.fnmatch(item_name, clean_pattern) or fnmatch.fnmatch(rel_path, clean_pattern)
        ):
            return True
    return False

def is_valid_item(item, base_dir, show_hidden, excludes, text_only):
    if not show_hidden and item.name.startswith('.'): 
        return False
    # 返回 False 才能真正拦截
    if matches_exclude_pattern(item, base_dir, excludes):
        return False
    if text_only and item.is_file() and not is_text_file(item): 
        return False
    return True

def safe_read_text(file_path, quiet=False):
    if is_binary_content(file_path):
        return None

    encodings = ['utf-8', 'gbk', 'big5', 'utf-16', 'latin-1']
    
    for enc in encodings:
        try:
            with open(file_path, 'r', encoding=enc, errors='strict') as f:
                return f.read()
        except (UnicodeDecodeError, LookupError):
            continue

    if not quiet:
        logger.warning(f"Skipped {file_path.name}: Unsupported encoding.")
    return None

def scan_dir_lines(dir_path, prefix="", max_depth=None, current_depth=0, show_hidden=False, excludes=None, stats=None, highlights=None, text_only=False, quiet=False):
    if excludes is None: excludes = []
    if stats is None: stats = {"dirs": 0, "files": 0}
    if highlights is None: highlights = set()
        
    lines = []
    path = Path(dir_path)
    base_dir = path.resolve()  # 扫描的根目录
    seen_real_paths = set()
    try:
        seen_real_paths.add(base_dir)
    except FileNotFoundError:
        pass

    def get_valid_children(p):
        valid_items = [
            item for item in p.iterdir() 
            # 优雅的过滤写法
            if is_valid_item(item, base_dir, show_hidden, excludes, text_only)
        ]
        valid_items.sort(key=lambda x: (not x.is_dir(), x.name.lower()))
        return valid_items

    try:
        initial_items = get_valid_children(path)
    except PermissionError:
        lines.append(f"{prefix}[Permission Denied - Cannot read directory]")
        return lines

    stack = []
    for i in range(len(initial_items) - 1, -1, -1):
        item = initial_items[i]
        is_last = (i == len(initial_items) - 1)
        stack.append((item, current_depth + 1, prefix, is_last))

    while stack:
        item, depth, curr_prefix, is_last = stack.pop()

        if depth > HARD_DEPTH_LIMIT:
            if not quiet: lines.append(f"{curr_prefix}└── ⚠️ [SYSTEM MAX DEPTH REACHED]")
            continue
        
        connector = "└── " if is_last else "├── "
        symlink_mark = " (symlink)" if item.is_symlink() else ""
        match_mark = " 🎯 [MATCHED]" if item in highlights else ""
        display_name = f"{item.name}/" if item.is_dir() else item.name
        
        lines.append(f"{curr_prefix}{connector}{display_name}{symlink_mark}{match_mark}")
        
        if item.is_dir(): stats["dirs"] += 1
        else: stats["files"] += 1
            
        total_scanned = stats["dirs"] + stats["files"]
        if not quiet and total_scanned % 15 == 0:
            print_progress_bar(total_scanned, label="Scanning", icon="⏳")

        if item.is_dir() and not item.is_symlink():
            if max_depth is not None and depth > max_depth:
                continue  
            
            try:
                real_path = item.resolve(strict=True)
                if real_path in seen_real_paths:
                    if not quiet:
                        lines.append(f"{curr_prefix}    └── 🔄 [Recursion Blocked - Directory Loop Detected]")
                    continue  
                seen_real_paths.add(real_path)
            except Exception:
                pass

            try:
                children = get_valid_children(item)
            except PermissionError:
                extension = "    " if is_last else "│   "
                lines.append(f"{curr_prefix}{extension}[Permission Denied - Cannot read directory]")
                continue
                
            extension = "    " if is_last else "│   "
            new_prefix = curr_prefix + extension
            
            for i in range(len(children) - 1, -1, -1):
                child = children[i]
                child_is_last = (i == len(children) - 1)
                stack.append((child, depth + 1, new_prefix, child_is_last))
                
    return lines

def search_items(dir_path, keyword, show_hidden=False, excludes=None, text_only=False, quiet=False):
    if excludes is None: excludes = []

    exact_matches = []
    all_names_with_path = [] 
    keyword_lower = keyword.lower()
    scan_stats = {"count": 0}  
    base_dir = Path(dir_path).resolve()  # 扫描的根目录

    stack = [Path(dir_path)]
    seen_paths = set() 

    while stack:
        current_path = stack.pop()
        try:
            for item in current_path.iterdir():
                if item in seen_paths: continue
                seen_paths.add(item)

                if not is_valid_item(item, base_dir, show_hidden, excludes, text_only):
                    continue

                scan_stats["count"] += 1
                all_names_with_path.append((item.name, item))        

                if keyword_lower in item.name.lower():
                    exact_matches.append(item)        

                if not quiet and scan_stats["count"] % 10 == 0:
                    print_progress_bar(scan_stats["count"], label="Searching", icon="🔍")

                if item.is_dir() and not item.is_symlink():
                    stack.append(item)
        except PermissionError: pass

    if not quiet:
        sys.stdout.write(f"\r✅ Search complete! Scanned {scan_stats['count']} items.                \n")
        sys.stdout.flush()

    exact_match_paths = {ex.resolve() for ex in exact_matches}
    unique_names_for_fuzzy = list(set([name for name, path in all_names_with_path if path.resolve() not in exact_match_paths]))
    close_names = difflib.get_close_matches(keyword, unique_names_for_fuzzy, n=10, cutoff=0.8)
    close_names_set = set(close_names)

    fuzzy_matches = []
    fuzzy_seen = set()

    for name, path in all_names_with_path:
        p_res = path.resolve()
        if name in close_names_set and p_res not in exact_match_paths and p_res not in fuzzy_seen:
            fuzzy_matches.append(path)
            fuzzy_seen.add(p_res)

    return exact_matches, fuzzy_matches

def get_full_context(target_path, show_hidden=False, excludes=None, text_only=False, max_depth=None, quiet=False):
    if excludes is None: excludes = []
    context_data = []
    
    dynamic_mem_limit_mb = get_system_mem_limit_mb()
    TOTAL_MAX_MEMORY = dynamic_mem_limit_mb * 1024 * 1024
    current_total_memory = 0
    base_dir = Path(target_path).resolve()  # 扫描的根目录
    
    stack = [(Path(target_path), 0)]
    
    while stack:
        current_path, current_depth = stack.pop()
        
        effective_depth = max_depth if max_depth is not None else HARD_DEPTH_LIMIT
        if current_depth > effective_depth or current_depth > HARD_DEPTH_LIMIT:
            continue
            
        try:
            items = sorted(list(current_path.iterdir()), key=lambda x: (not x.is_dir(), x.name.lower()))
            for item in items:
                if not is_valid_item(item, base_dir, show_hidden, excludes, text_only): 
                    continue
                    
                if item.is_file():
                    try:
                        f_stat = item.stat()
                        if f_stat.st_size > MAX_FILE_SIZE: continue
                        
                        if current_total_memory + f_stat.st_size > TOTAL_MAX_MEMORY:
                            logger.error(f"Hardware memory safety limit ({dynamic_mem_limit_mb}MB) reached! Aborting further reads to protect system RAM.")
                            return context_data

                        content = safe_read_text(item, quiet=quiet)
                        if content is not None:
                            content_size = len(content.encode('utf-8'))
                            
                            if current_total_memory + content_size > TOTAL_MAX_MEMORY:
                                logger.error(f"Hardware memory safety limit ({dynamic_mem_limit_mb}MB) reached after text decoding! Aborting further reads.")
                                return context_data
                                
                            context_data.append((item.relative_to(target_path), content))
                            current_total_memory += content_size  
                    except Exception: pass
                elif item.is_dir() and not item.is_symlink():
                    stack.append((item, current_depth + 1))
        except PermissionError: pass
        
    return context_data