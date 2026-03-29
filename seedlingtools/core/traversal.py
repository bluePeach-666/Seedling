from __future__ import annotations
import sys
from abc import ABC, abstractmethod
from pathlib import Path
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple, Set
from .config import ScanConfig
from .patterns import validate_scan_target, detect_text_file
from ..utils import (
    FileSettings,
    logger,
    terminal,
    get_memory_limit_mb,
    io_processor
)

@dataclass
class TraversalItem:
    """遍历过程中发现的单个项目实体"""
    path: Path
    relative_path: Path
    is_dir: bool
    is_symlink: bool
    depth: int

@dataclass
class TraversalResult:
    """单次遍历任务的数据聚合结果"""
    items: List[TraversalItem] = field(default_factory=list)
    text_files: List[TraversalItem] = field(default_factory=list)
    directories: List[TraversalItem] = field(default_factory=list)
    stats: Dict[str, int] = field(default_factory=lambda: {"dirs": 0, "files": 0})

    _content_cache: Dict[Path, Optional[str]] = field(default_factory=dict)
    _mem_usage: int = field(default=0, repr=False)
    _mem_limit: int = field(default=0, repr=False)

    @property
    def estimated_tokens(self) -> int:
        """
        [v2.5.1 预留接口] Token 估算引擎。
        当前版本仅作为占位符返回 0。
        """
        return 0
    
    def get_content(self, item: TraversalItem, quiet: bool = False) -> Optional[str]:
        if item.is_dir:
            return None

        if item.path not in self._content_cache:
            self._content_cache[item.path] = io_processor.read_text_safely(
                item.path, 
                quiet=quiet
            )
        return self._content_cache[item.path]

    def can_allocate_memory(self, estimated_size: int) -> bool:
        if self._mem_limit == 0:
            return True
        return (self._mem_usage + estimated_size) <= self._mem_limit

    def register_content_cache(self, path: Path, content: Optional[str], size: int) -> None:
        self._content_cache[path] = content
        if content:
            self._mem_usage += size

class AbstractTraverser(ABC):
    """目录遍历引擎抽象接口"""
    
    @abstractmethod
    def traverse(
        self, 
        dir_path: Path, 
        config: ScanConfig, 
        collect_content: bool = False, 
        content_limit_mb: Optional[int] = None
    ) -> TraversalResult:
        """执行目录结构遍历并聚合数据"""
        pass


class AbstractTreeRenderer(ABC):
    """树状结构渲染引擎抽象接口"""

    @abstractmethod
    def render(self, result: TraversalResult, config: ScanConfig, root_path: Optional[Path] = None) -> List[str]:
        """将遍历结果渲染为文本格式的树状结构"""
        pass

class DepthFirstTraverser(AbstractTraverser):
    """基于深度优先搜索的遍历引擎具体实现"""

    def traverse(
        self,
        dir_path: Path,
        config: ScanConfig,
        collect_content: bool = False,
        content_limit_mb: Optional[int] = None
    ) -> TraversalResult:
        
        result = TraversalResult()

        if collect_content:
            limit_mb: int = content_limit_mb if content_limit_mb else get_memory_limit_mb()
            result._mem_limit = int(limit_mb * 1024 * 1024 * 0.8)  

        base_dir: Path = dir_path.resolve()
        seen_real_paths: Set[Path] = {base_dir}
        stack: List[Tuple[Path, int]] = [(base_dir, 0)] 

        while stack:
            curr, depth = stack.pop()
            
            if config.max_depth is not None and depth > config.max_depth:
                continue

            if depth > FileSettings.HARD_DEPTH_LIMIT:
                logger.warning(f"System maximum depth boundary reached at {curr}")
                continue

            try:
                items: List[Path] = sorted(
                    list(curr.iterdir()),
                    key=lambda x: (not x.is_dir(), x.name.lower())
                )

                for item in items:
                    if not validate_scan_target(item, base_dir, config):
                        continue

                    item_depth: int = depth + 1
                    rel_path: Path = item.relative_to(base_dir)
                    
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

                        if detect_text_file(item):
                            result.text_files.append(trav_item)

                            if collect_content:
                                self._process_content_caching(item, result, config)

                    total_scanned: int = result.stats["dirs"] + result.stats["files"]
                    if total_scanned % 15 == 0:
                        terminal.render_progress(total_scanned, label="Scanning", quiet=config.quiet)

                    if item.is_dir() and not item.is_symlink():
                        if config.max_depth is not None and item_depth >= config.max_depth:
                            continue

                        try:
                            real_path: Path = item.resolve(strict=True)
                            if real_path in seen_real_paths:
                                continue  
                            seen_real_paths.add(real_path)
                            stack.append((item, item_depth))
                        except (OSError, RuntimeError):
                            pass

            except PermissionError:
                pass 
            except OSError as err:
                logger.debug(f"Traversal interrupted at {curr}: {err}")

        return result

    def _process_content_caching(self, item: Path, result: TraversalResult, config: ScanConfig) -> None:
        """内部辅助处理文件内容的内存分配与缓存"""
        try:
            f_stat = item.stat()
            if f_stat.st_size <= FileSettings.MAX_FILE_SIZE:
                estimated_memory: int = f_stat.st_size * 2  
                if result.can_allocate_memory(estimated_memory):
                    content: Optional[str] = io_processor.read_text_safely(item, quiet=config.quiet)
                    if content:
                        actual_size: int = sys.getsizeof(content)
                        if result.can_allocate_memory(actual_size):
                            result.register_content_cache(item, content, actual_size)
        except OSError:
            pass


class StandardTreeRenderer(AbstractTreeRenderer):
    """标准控制台树状结构渲染器"""

    def render(self, result: TraversalResult, config: ScanConfig, root_path: Optional[Path] = None) -> List[str]:
        lines: List[str] = []

        if not result.items:
            return lines

        if root_path is None:
            min_depth: int = min(item.depth for item in result.items)
            root_level_items: List[TraversalItem] = [item for item in result.items if item.depth == min_depth]
            if root_level_items:
                root_path = root_level_items[0].path.parent

        items_by_parent: Dict[Path, List[TraversalItem]] = {}
        for item in result.items:
            parent: Path = item.path.parent
            items_by_parent.setdefault(parent, []).append(item)

        def _build_subtree(items: List[TraversalItem], prefix: str = "") -> None:
            items.sort(key=lambda x: (not x.is_dir, x.path.name.lower()))

            for i, item in enumerate(items):
                is_last: bool = (i == len(items) - 1)
                connector: str = "└── " if is_last else "├── "
                
                symlink_mark: str = " (symlink)" if item.is_symlink else ""
                match_mark: str = " [MATCHED]" if item.path in config.highlights else ""
                display_name: str = f"{item.path.name}/" if item.is_dir else item.path.name

                lines.append(f"{prefix}{connector}{display_name}{symlink_mark}{match_mark}")

                if item.is_dir:
                    children: List[TraversalItem] = items_by_parent.get(item.path, [])
                    if children:
                        new_prefix: str = prefix + ("    " if is_last else "│   ")
                        _build_subtree(children, new_prefix)

        if root_path and root_path in items_by_parent:
            _build_subtree(items_by_parent[root_path])

        return lines