from __future__ import annotations
import sys
from abc import ABC, abstractmethod
from pathlib import Path
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple, Set, Any

from .config import ScanConfig
from .patterns import matcher_engine
from ..utils import (
    FileSettings,
    logger,
    terminal,
    get_memory_limit_mb,
    io_processor
)

@dataclass
class TraversalItem:
    path: Path
    relative_path: Path
    is_dir: bool
    is_symlink: bool
    depth: int

@dataclass
class TraversalResult:
    items: List[TraversalItem] = field(default_factory=list)
    text_files: List[TraversalItem] = field(default_factory=list)
    directories: List[TraversalItem] = field(default_factory=list)
    stats: Dict[str, int] = field(default_factory=lambda: {"dirs": 0, "files": 0})

    _content_cache: Dict[Path, Optional[str]] = field(default_factory=dict)
    _mem_usage: int = field(default=0, repr=False)
    _mem_limit: int = field(default=0, repr=False)
    _total_tokens: int = field(default=0, repr=False)

    @property
    def estimated_tokens(self) -> int:
        return self._total_tokens
    
    def get_content(self, item: TraversalItem, quiet: bool = False) -> Optional[str]:
        if item.is_dir is True:
            return None

        if item.path not in self._content_cache:
            content: Optional[str] = io_processor.read_text_safely(
                item.path, 
                quiet=quiet
            )
            self._content_cache[item.path] = content
            
            if content is not None:
                token_count: int = len(content) // 4
                self._total_tokens += token_count

        return self._content_cache[item.path]

    def can_allocate_memory(self, estimated_size: int) -> bool:
        if self._mem_limit == 0:
            return True
            
        if (self._mem_usage + estimated_size) <= self._mem_limit:
            return True
        else:
            return False

    def register_content_cache(self, path: Path, content: Optional[str], size: int) -> None:
        self._content_cache[path] = content
        if content is not None:
            self._mem_usage += size
            token_count: int = len(content) // 4
            self._total_tokens += token_count

class AbstractTraverser(ABC):
    @abstractmethod
    def traverse(
        self, 
        dir_path: Path, 
        config: ScanConfig, 
        collect_content: bool = False, 
        content_limit_mb: Optional[int] = None
    ) -> TraversalResult:
        pass

class AbstractTreeRenderer(ABC):
    @abstractmethod
    def render(self, result: TraversalResult, config: ScanConfig, root_path: Optional[Path] = None) -> List[str]:
        pass

class DepthFirstTraverser(AbstractTraverser):
    def traverse(
        self,
        dir_path: Path,
        config: ScanConfig,
        collect_content: bool = False,
        content_limit_mb: Optional[int] = None
    ) -> TraversalResult:
        
        result = TraversalResult()

        if collect_content is True:
            limit_mb: int = 0
            if content_limit_mb is not None:
                limit_mb = content_limit_mb
            else:
                limit_mb = get_memory_limit_mb()
            result._mem_limit = int(limit_mb * 1024 * 1024 * 0.8)  

        base_dir: Path = dir_path.resolve()
        seen_real_paths: Set[Path] = {base_dir}
        stack: List[Tuple[Path, int]] = [(base_dir, 0)] 

        def _sort_key(x: Path) -> Tuple[bool, str]:
            return (x.is_dir() is False, x.name.lower())

        while len(stack) > 0:
            curr_item: Tuple[Path, int] = stack.pop()
            curr: Path = curr_item[0]
            depth: int = curr_item[1]
            
            if config.max_depth is not None:
                if depth > config.max_depth:
                    continue

            if depth > FileSettings.HARD_DEPTH_LIMIT:
                logger.warning(f"System maximum depth boundary reached at {curr}")
                continue

            try:
                raw_items: List[Path] = list(curr.iterdir())
                items: List[Path] = sorted(raw_items, key=_sort_key)

                for item in items:
                    if matcher_engine.validate_scan_target(item, base_dir, config) is False:
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

                    if item.is_dir() is True:
                        result.stats["dirs"] += 1
                        result.directories.append(trav_item)
                    else:
                        result.stats["files"] += 1

                        if matcher_engine.detect_text_file(item) is True:
                            result.text_files.append(trav_item)

                            if collect_content is True:
                                self._process_content_caching(item, result, config)

                    total_scanned: int = result.stats["dirs"] + result.stats["files"]
                    if (total_scanned % 15) == 0:
                        terminal.render_progress(total_scanned, label="Scanning", quiet=config.quiet)

                    if item.is_dir() is True:
                        if item.is_symlink() is False:
                            should_explore: bool = True
                            if config.max_depth is not None:
                                if item_depth >= config.max_depth:
                                    should_explore = False
                                    
                            if should_explore is True:
                                try:
                                    real_path: Path = item.resolve(strict=True)
                                    if real_path not in seen_real_paths:
                                        seen_real_paths.add(real_path)
                                        stack.append((item, item_depth))
                                except OSError:
                                    pass
                                except RuntimeError:
                                    pass

            except PermissionError:
                pass 
            except OSError as err:
                logger.debug(f"Traversal interrupted at {curr}: {err}")

        return result

    def _process_content_caching(self, item: Path, result: TraversalResult, config: ScanConfig) -> None:
        try:
            f_stat: Any = item.stat()
            if f_stat.st_size <= FileSettings.MAX_FILE_SIZE:
                estimated_memory: int = f_stat.st_size * 2  
                if result.can_allocate_memory(estimated_memory) is True:
                    content: Optional[str] = io_processor.read_text_safely(item, quiet=config.quiet)
                    if content is not None:
                        actual_size: int = sys.getsizeof(content)
                        if result.can_allocate_memory(actual_size) is True:
                            result.register_content_cache(item, content, actual_size)
        except OSError:
            pass

class StandardTreeRenderer(AbstractTreeRenderer):
    def render(self, result: TraversalResult, config: ScanConfig, root_path: Optional[Path] = None) -> List[str]:
        lines: List[str] = []

        if len(result.items) == 0:
            return lines

        if root_path is None:
            min_depth: int = min(item.depth for item in result.items)
            root_level_items: List[TraversalItem] = []
            for item in result.items:
                if item.depth == min_depth:
                    root_level_items.append(item)
            if len(root_level_items) > 0:
                root_path = root_level_items[0].path.parent

        items_by_parent: Dict[Path, List[TraversalItem]] = {}
        for item in result.items:
            parent: Path = item.path.parent
            if parent not in items_by_parent:
                items_by_parent[parent] = []
            items_by_parent[parent].append(item)

        def _sort_item_key(x: TraversalItem) -> Tuple[bool, str]:
            return (x.is_dir is False, x.path.name.lower())

        def _build_subtree(items: List[TraversalItem], prefix: str = "") -> None:
            items.sort(key=_sort_item_key)

            for i, item in enumerate(items):
                is_last: bool = False
                if i == (len(items) - 1):
                    is_last = True
                
                connector: str = ""
                if is_last is True:
                    connector = "└── "
                else:
                    connector = "├── "
                
                symlink_mark: str = ""
                if item.is_symlink is True:
                    symlink_mark = " (symlink)"
                    
                match_mark: str = ""
                if item.path in config.highlights:
                    match_mark = " [MATCHED]"
                    
                display_name: str = ""
                if item.is_dir is True:
                    display_name = f"{item.path.name}/"
                else:
                    display_name = item.path.name

                lines.append(f"{prefix}{connector}{display_name}{symlink_mark}{match_mark}")

                if item.is_dir is True:
                    children: List[TraversalItem] = items_by_parent.get(item.path, [])
                    if len(children) > 0:
                        new_prefix: str = prefix
                        if is_last is True:
                            new_prefix = new_prefix + "    "
                        else:
                            new_prefix = new_prefix + "│   "
                        _build_subtree(children, new_prefix)

        if root_path is not None:
            if root_path in items_by_parent:
                _build_subtree(items_by_parent[root_path])

        return lines