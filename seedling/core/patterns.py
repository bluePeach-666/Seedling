import fnmatch
from pathlib import Path
from typing import List
from .config import ScanConfig, FILE_TYPE_MAP
from .detection import is_text_file

def matches_exclude_pattern(item_path: Path, base_dir: Path, exclude_patterns: List[str]) -> bool:
    """路径是否匹配 Git 格式"""
    rel_path = "/" + item_path.relative_to(base_dir).as_posix()
    item_name = item_path.name

    # 遍历排除规则
    for pattern in exclude_patterns:
        is_dir_only = pattern.endswith('/')
        clean_pattern = pattern.rstrip('/')

        # 路径锚定
        if clean_pattern.startswith('/'):
            if fnmatch.fnmatch(rel_path, clean_pattern):
                # 目录规则仅匹配目录，文件规则匹配文件/目录
                if not is_dir_only or item_path.is_dir():
                    return True

        # 全局匹配
        else:
            # 匹配文件/目录名称
            if fnmatch.fnmatch(item_name, clean_pattern):
                if not is_dir_only or item_path.is_dir():
                    return True
            # 匹配路径片段
            if fnmatch.fnmatch(rel_path, f"*/{clean_pattern}") or \
               fnmatch.fnmatch(rel_path, f"*/{clean_pattern}/*") or \
               fnmatch.fnmatch(rel_path, f"**/{clean_pattern}"):
                if not is_dir_only or item_path.is_dir():
                    return True
    return False

def matches_include_pattern(item_path: Path, base_dir: Path, include_patterns: List[str]) -> bool:
    """路径是否匹配包含过滤规则"""
    if not include_patterns:
        return True

    rel_path = item_path.relative_to(base_dir)
    item_name = item_path.name 

    for pattern in include_patterns:
        clean = pattern.lstrip('/')

        # 直接匹配文件名称
        if fnmatch.fnmatch(item_name, clean):
            return True

        # pathlib 匹配通配符
        try:
            if rel_path.match(pattern) or rel_path.match(clean):
                return True
            if pattern.startswith('**/'):
                if rel_path.match(pattern[3:]):
                    return True
        except (ValueError, TypeError):
            pass

        # 匹配路径片段
        rel_str = rel_path.as_posix()
        if fnmatch.fnmatch(rel_str, clean) or fnmatch.fnmatch(rel_str, f"*/{clean}"):
            return True
    return False

def is_valid_item(item: Path, base_dir: Path, config: ScanConfig) -> bool:
    """判断是否纳入扫描结果"""
    if not config.show_hidden and item.name.startswith('.'): # 隐藏过滤
        return False
    if matches_exclude_pattern(item, base_dir, config.excludes): # 排除规则过滤
        return False
    if config.includes and item.is_file(): # 包含规则过滤
        if not matches_include_pattern(item, base_dir, config.includes):
            return False
    if config.file_type and item.is_file(): # 文件类型过滤
        allowed = FILE_TYPE_MAP.get(config.file_type.lower())
        if allowed and item.suffix.lower() not in allowed:
            return False
    if config.text_only and item.is_file() and not is_text_file(item): # 纯文本文件过滤
        return False
    return True
