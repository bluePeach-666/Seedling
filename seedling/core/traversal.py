import sys
from pathlib import Path
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple

from .config import ScanConfig, MAX_FILE_SIZE, HARD_DEPTH_LIMIT
from .detection import is_text_file, is_binary_content
from .patterns import is_valid_item
from .ui import print_progress_bar
from .logger import logger
from .sysinfo import get_system_mem_limit_mb

@dataclass
class TraversalItem:
    """在遍历过程中发现的单个项目"""
    path: Path               # 绝对路径
    relative_path: Path      # 相对路径
    is_dir: bool             # 是否为目录
    is_symlink: bool         # 是否为符号链接
    depth: int               # 目录深度


@dataclass
class TraversalResult:
    """单次遍历结果"""
    items: List[TraversalItem] = field(default_factory=list)        # 所有发现的项目列表
    text_files: List[TraversalItem] = field(default_factory=list)   # 文本文件列表
    directories: List[TraversalItem] = field(default_factory=list)  # 目录列表
    stats: Dict[str, int] = field(default_factory=lambda: {"dirs": 0, "files": 0}) # 目录和文件数量

    _content_cache: Dict[Path, Optional[str]] = field(default_factory=dict)
    _mem_usage: int = field(default=0, repr=False)   # 当前缓存占用的内存量
    _mem_limit: int = field(default=0, repr=False)   # 允许的最大内存使用量

    def get_content(self, item: TraversalItem, quiet: bool = False) -> Optional[str]:
        """获取文件内容"""
        if item.is_dir:
            return None

        # 如果缓存中没有该文件，则读取并存入缓存
        if item.path not in self._content_cache:
            self._content_cache[item.path] = _safe_read_text_cached(
                item.path, quiet=quiet
            )
        return self._content_cache[item.path]

    def can_add_content(self, estimated_size: int) -> bool:
        """是否可以在内存限制范围内继续添加文件内容"""
        if self._mem_limit == 0: # 上限为0代表无内存限制
            return True
        return self._mem_usage + estimated_size <= self._mem_limit

    def add_to_cache(self, path: Path, content: Optional[str], size: int):
        """添加缓存并更新当前的内存占用"""
        self._content_cache[path] = content
        if content:
            self._mem_usage += size


def _safe_read_text_cached(file_path: Path, quiet: bool = False) -> Optional[str]:
    """文本读取"""
    if is_binary_content(file_path):
        return None # 忽略二进制文件

    # 尝试编码
    encodings = ['utf-8', 'gbk', 'big5', 'utf-16', 'latin-1']
    for enc in encodings:
        try:
            with open(file_path, 'r', encoding=enc, errors='strict') as f:
                return f.read()
        except (UnicodeDecodeError, LookupError):
            continue 

    # 记录警告
    if not quiet:
        logger.warning(f"Skipped {file_path.name}: Unsupported encoding.")
    return None


def traverse_directory(
    dir_path: Path,
    config: ScanConfig,
    collect_content: bool = False,
    content_limit_mb: Optional[int] = None
) -> TraversalResult:
    """DFS遍历"""
    result = TraversalResult()

    # 如果开启了收集文件内容，则初始化内存限制
    if collect_content:
        limit_mb = content_limit_mb or get_system_mem_limit_mb()
        result._mem_limit = int(limit_mb * 1024 * 1024 * 0.8)  

    base_dir = dir_path.resolve()
    seen_real_paths = {base_dir} # 记录真实物理路径
    resolved_start = dir_path.resolve()
    stack: List[Tuple[Path, int]] = [(resolved_start, 0)] 

    while stack:
        curr, depth = stack.pop()
        if config.max_depth is not None and depth > config.max_depth:
            continue

        if depth > HARD_DEPTH_LIMIT:
            logger.warning(f"System max depth reached at {curr}")
            continue

        try:
            # 优先显示文件夹，然后按名称字母顺序排序
            items = sorted(
                list(curr.iterdir()),
                key=lambda x: (not x.is_dir(), x.name.lower())
            )

            for item in items:
                # 过滤无效项目
                if not is_valid_item(item, base_dir, config):
                    continue

                # 计算子项目的深度
                item_depth = depth + 1

                # 实例化一个 TraversalItem
                rel_path = item.relative_to(base_dir)
                trav_item = TraversalItem(
                    path=item,
                    relative_path=rel_path,
                    is_dir=item.is_dir(),
                    is_symlink=item.is_symlink(),
                    depth=item_depth
                )

                result.items.append(trav_item)

                if item.is_dir():
                    result.stats["dirs"] += 1
                    result.directories.append(trav_item)
                else:
                    result.stats["files"] += 1

                    # 记录文本文件
                    if is_text_file(item):
                        result.text_files.append(trav_item)

                        # 如果允许收集内容，则读取文件到缓存
                        if collect_content:
                            try:
                                f_stat = item.stat()
                                if f_stat.st_size <= MAX_FILE_SIZE:
                                    estimated = f_stat.st_size * 2  
                                    if result.can_add_content(estimated):
                                        content = _safe_read_text_cached(item, quiet=config.quiet)
                                        if content:
                                            # 获取读取后字符串的精确内存大小
                                            actual_size = sys.getsizeof(content)
                                            if result.can_add_content(actual_size):
                                                result.add_to_cache(item, content, actual_size)
                            except Exception:
                                pass 

                total = result.stats["dirs"] + result.stats["files"]
                if total % 15 == 0:
                    print_progress_bar(total, label="Scanning", quiet=config.quiet)

                if item.is_dir() and not item.is_symlink():
                    # 压栈前预先检查深度
                    if config.max_depth is not None and item_depth >= config.max_depth:
                        continue

                    try:
                        real_path = item.resolve(strict=True)
                        if real_path in seen_real_paths:
                            continue  # 避免死循环递归
                        seen_real_paths.add(real_path)
                    except Exception:
                        pass

                    stack.append((item, item_depth))

        except PermissionError:
            pass # 忽略没有读取权限的目录

    return result


def build_tree_lines(result: TraversalResult, config: ScanConfig, root_path: Optional[Path] = None) -> List[str]:
    """根据 TraversalResult 构建文本格式的树状结构字符串"""
    lines = []

    if not result.items:
        return lines

    # 如果没有指定根路径，则尝试从已有的项目列表中推导出来
    if root_path is None and result.items:
        # 查找深度最浅的项，获取它们的共同父目录作为根目录
        min_depth = min(item.depth for item in result.items)
        root_level_items = [item for item in result.items if item.depth == min_depth]
        if root_level_items:
            # 顶级项目的父目录即为根目录
            root_path = root_level_items[0].path.parent

    # 将所有项目按照其父目录进行分组，用于分层渲染
    items_by_parent: Dict[Path, List[TraversalItem]] = {}

    for item in result.items:
        parent = item.path.parent
        if parent not in items_by_parent:
            items_by_parent[parent] = []
        items_by_parent[parent].append(item)

    # 递归生成树结构的内部函数
    def _build_subtree(items: List[TraversalItem], prefix: str = ""):
        # 目录在前，文件在后，字母顺序排序
        items.sort(key=lambda x: (not x.is_dir, x.path.name.lower()))

        for i, item in enumerate(items):
            is_last = (i == len(items) - 1)
            connector = "└── " if is_last else "├── "
            symlink_mark = " (symlink)" if item.is_symlink else ""
            match_mark = " 🎯 [MATCHED]" if item.path in config.highlights else ""
            display_name = f"{item.path.name}/" if item.is_dir else item.path.name

            lines.append(f"{prefix}{connector}{display_name}{symlink_mark}{match_mark}")

            # 递归处理所有子项目
            if item.is_dir:
                children = items_by_parent.get(item.path, [])
                if children:
                    new_prefix = prefix + ("    " if is_last else "│   ")
                    _build_subtree(children, new_prefix)

    # 从根级项目开始构建树
    if root_path and root_path in items_by_parent:
        root_items = items_by_parent[root_path]
        _build_subtree(root_items)

    return lines
