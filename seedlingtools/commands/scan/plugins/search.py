from __future__ import annotations
import sys
from pathlib import Path
from typing import List, Optional, Tuple, Any, Final
from ..base import AbstractScanPlugin
from ....core import (
    ScanConfig, 
    TraversalResult, 
    StandardTreeRenderer, 
    fuzzy_match_candidates,
    evaluate_regex_rule,
    evaluate_exact_rule
)
from ....utils import (
    is_relative_to_compat,
    logger, 
    terminal, 
    io_processor, 
    image_renderer,
    FileSystemError, 
    ConfigurationError
)

class SearchPlugin(AbstractScanPlugin):
    """支持正则/模糊匹配、交互式危险删除以及高亮报告生成的深度搜索插件"""

    def __init__(self, keyword: str, delete_mode: bool = False, dry_run: bool = False) -> None:
        self.keyword: str = keyword
        self.delete_mode: bool = delete_mode
        self.dry_run: bool = dry_run
        self.tree_renderer: Final[StandardTreeRenderer] = StandardTreeRenderer()

    def execute(self, target_path: Path, config: ScanConfig, result: TraversalResult, **kwargs: Any) -> None:
        if not self.keyword:
            raise ConfigurationError("Search keyword cannot be empty.")

        if self.delete_mode and not sys.stdin.isatty():
            logger.error("Dangerous operation '--delete' can only be used in an interactive terminal.")
            return
        
        # 匹配逻辑
        exact_matches, fuzzy_matches = self._perform_matching_logic(result, config)
        all_matches: List[Path] = exact_matches + fuzzy_matches

        if not all_matches:
            logger.info(f"No matches found for keyword: '{self.keyword}'")
            return

        self._display_results_to_console(exact_matches, fuzzy_matches, target_path)

        # 删除逻辑拦截
        if self.delete_mode:
            self._execute_interactive_deletion(exact_matches, fuzzy_matches, target_path)
            return

        # 动态报告生成
        if kwargs.get('is_full', False):
            format_type: str = kwargs.get('format', 'md')
            ext_map: Final[dict[str, str]] = {'md': '.md', 'txt': '.txt', 'image': '.png'}
            suffix: str = ext_map.get(format_type, '.md')
            
            # 图片放不下全量源码，强制降级为 md
            if format_type == 'image':
                logger.warning("Search report with full source code cannot be rendered as an image. Falling back to Markdown.")
                format_type = 'md'
                suffix = '.md'

            out_file: Path = kwargs.get('out_file', Path.cwd() / f"search_report_{self.keyword}{suffix}")
            self._generate_contextual_report(
                all_matches, exact_matches, fuzzy_matches, 
                target_path, config, result, out_file, format_type)
            
    def _perform_matching_logic(self, result: TraversalResult, config: ScanConfig) -> Tuple[List[Path], List[Path]]:
        """调用 Core 层的匹配引擎"""
        exact: List[Path] = []
        candidates: List[Tuple[str, Path]] = []
        
        for item in result.items:
            name: str = item.path.name
            matched: bool = False
            
            # 分发匹配策略
            if config.use_regex:
                matched = evaluate_regex_rule(target=name, pattern=self.keyword, ignore_case=True)
            else:
                matched = evaluate_exact_rule(target=name, keyword=self.keyword, ignore_case=True)
            
            if matched:
                exact.append(item.path)
            else:
                candidates.append((name, item.path))

        fuzzy: List[Path] = []
        
        if not config.use_regex:
            if candidates:
                unique_names: List[str] = []
                for n, p in candidates:
                    if n not in unique_names:
                        unique_names.append(n)
                        
                close_names: List[str] = fuzzy_match_candidates(
                    target=self.keyword, 
                    candidates=unique_names, 
                    cutoff=0.7, 
                    limit=10
                )
                
                for n, p in candidates:
                    if n in close_names:
                        fuzzy.append(p)
            
        return exact, fuzzy
    
    def _display_results_to_console(self, exact: List[Path], fuzzy: List[Path], target_path: Path) -> None:
        """格式化输出匹配项到终端"""
        def _fmt(p: Path) -> str:
            rel = p.relative_to(target_path) if is_relative_to_compat(p, target_path) else p
            icon = "[DIR]" if p.is_dir() else "[FILE]"
            return f"  {icon} {rel}"

        if exact:
            logger.info(f"Exact matches for '{self.keyword}':")
            for item in exact[:20]:
                logger.info(_fmt(item))
        
        if fuzzy:
            logger.info(f"Potential candidates (Fuzzy matches):")
            for item in fuzzy[:10]:
                logger.info(_fmt(item))

    def _execute_interactive_deletion(self, exact: List[Path], fuzzy: List[Path], target_path: Path) -> None:
        all_to_delete: List[Path] = list(exact)
        if fuzzy:
            logger.warning("Fuzzy matches may include unintended items!")
            if terminal.prompt_confirmation("Do you want to INCLUDE these fuzzy matches in the deletion? [y/n]: "):
                all_to_delete.extend(fuzzy)

        if not all_to_delete:
            logger.info("No items selected for deletion. Aborting.")
            return

        if self.dry_run:
            logger.info(f"[DRY-RUN] Targeted: {len(all_to_delete)} items.")
            for m in all_to_delete: 
                logger.info(f"  [WILL REMOVE] {m.relative_to(target_path) if is_relative_to_compat(m, target_path) else m.name}")
            return

        logger.warning(f"CRITICAL: You are about to PERMANENTLY DELETE {len(all_to_delete)} items.")
        confirm: str = input("Please type 'CONFIRM DELETE' to proceed: ").strip()
        
        if confirm == "CONFIRM DELETE":
            deleted_count: int = 0
            for item in all_to_delete:
                try:
                    io_processor.delete_path(item)
                    deleted_count += 1
                except FileSystemError as err:
                    logger.error(str(err))
            logger.info(f"Purge complete. {deleted_count} items removed from disk.")
        else:
            logger.info("Operation aborted. Security signature mismatch.")
            
    def _generate_contextual_report(
        self, 
        all_matches: List[Path], 
        exact: List[Path], 
        fuzzy: List[Path], 
        target_path: Path, 
        config: ScanConfig, 
        result: TraversalResult, 
        out_file: Path,
        format_type: str
    ) -> None:
        """生成支持多种格式的搜索报告"""
        
        # 准备树状文本
        config.highlights = set(all_matches)
        tree_lines: List[str] = self.tree_renderer.render(result, config, root_path=target_path)
        tree_text: str = f"{target_path.name}/\n" + "\n".join(tree_lines)

        # 图像分支处理
        if format_type == 'image':
            image_renderer.render_text_to_image(tree_text, out_file, len(tree_lines))
            return

        # 文本分支处理
        try:
            with open(out_file, 'w', encoding='utf-8') as f:
                if format_type == 'md':
                    f.write(f"# Search Report: {self.keyword}\n\n")
                    f.write("## Visual Topology\n```text\n" + tree_text + "\n```\n")
                else:
                    f.write(f"Search Report: {self.keyword}\n" + "="*40 + "\n" + tree_text + "\n")

                # 提取源码上下文
                f.write("\n" + "="*60 + "\nMATCHED SOURCE CONTENT\n" + "="*60 + "\n\n")
                for m in all_matches:
                    if m.is_dir(): continue
                    for item in result.text_files:
                        if item.path == m:
                            content = result.get_content(item, quiet=True)
                            if content:
                                if format_type == 'md':
                                    fence = io_processor.calculate_markdown_fence(content)
                                    f.write(f"### {item.relative_path}\n{fence}\n{content}\n{fence}\n\n")
                                else:
                                    f.write(f"--- FILE: {item.relative_path} ---\n{content}\n\n")
            
            logger.info(f"Report exported: {out_file.name}")
        except OSError as err:
            raise FileSystemError(f"Failed to write report: {err}")