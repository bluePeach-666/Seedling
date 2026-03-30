from __future__ import annotations
import sys
from pathlib import Path
from typing import List, Optional, Tuple, Any, Final

from ..base import AbstractScanPlugin
from ....core import ScanConfig, TraversalResult, StandardTreeRenderer, matcher_engine
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
    def __init__(self, keyword: str, delete_mode: bool = False, dry_run: bool = False) -> None:
        self.keyword: Final[str] = keyword
        self.delete_mode: Final[bool] = delete_mode
        self.dry_run: Final[bool] = dry_run
        self.tree_renderer: Final[StandardTreeRenderer] = StandardTreeRenderer()

    def execute(self, target_path: Path, config: ScanConfig, result: TraversalResult, **kwargs: Any) -> None:
        if len(self.keyword) == 0:
            raise ConfigurationError(message="Search keyword cannot be empty.")

        if self.delete_mode is True:
            if sys.stdin.isatty() is False:
                logger.error("Dangerous operation '--delete' can only be used in an interactive terminal.")
                return
        
        exact_matches: List[Path]
        fuzzy_matches: List[Path]
        exact_matches, fuzzy_matches = self._perform_matching_logic(result, config)
        
        all_matches: List[Path] = []
        for em in exact_matches:
            all_matches.append(em)
        for fm in fuzzy_matches:
            all_matches.append(fm)

        if len(all_matches) == 0:
            logger.info(f"No matches found for keyword: '{self.keyword}'")
            return

        self._display_results_to_console(exact_matches, fuzzy_matches, target_path)

        if self.delete_mode is True:
            self._execute_interactive_deletion(exact_matches, fuzzy_matches, target_path)
            return

        is_full: bool = False
        if 'is_full' in kwargs:
            if kwargs['is_full'] is True:
                is_full = True

        if is_full is True:
            format_type: str = 'md'
            if 'format' in kwargs:
                format_type = kwargs['format']
                
            ext_map: Final[dict[str, str]] = {'md': '.md', 'txt': '.txt', 'image': '.png'}
            suffix: str = '.md'
            if format_type in ext_map:
                suffix = ext_map[format_type]
            
            if format_type == 'image':
                logger.warning("Search report with full source code cannot be rendered as an image. Falling back to Markdown.")
                format_type = 'md'
                suffix = '.md'

            out_file: Path
            if 'out_file' in kwargs:
                out_file = kwargs['out_file']
            else:
                out_file = Path.cwd() / f"search_report_{self.keyword}{suffix}"
                
            self._generate_contextual_report(
                all_matches, exact_matches, fuzzy_matches, 
                target_path, config, result, out_file, format_type
            )
            
    def _perform_matching_logic(self, result: TraversalResult, config: ScanConfig) -> Tuple[List[Path], List[Path]]:
        exact: List[Path] = []
        candidates_names: List[str] = []
        candidates_paths: List[Path] = []
        
        for item in result.items:
            name: str = item.path.name
            matched: bool = False
            
            if config.use_regex is True:
                matched = matcher_engine.evaluate_regex_rule(target=name, pattern=self.keyword, ignore_case=True)
            else:
                matched = matcher_engine.evaluate_exact_rule(target=name, keyword=self.keyword, ignore_case=True)
            
            if matched is True:
                exact.append(item.path)
            else:
                candidates_names.append(name)
                candidates_paths.append(item.path)

        fuzzy: List[Path] = []
        
        if config.use_regex is False:
            if len(candidates_names) > 0:
                unique_names: List[str] = []
                for n in candidates_names:
                    if n not in unique_names:
                        unique_names.append(n)
                        
                close_names: List[str] = matcher_engine.fuzzy_match_candidates(
                    target=self.keyword, 
                    candidates=unique_names, 
                    cutoff=0.7, 
                    limit=10
                )
                
                for i in range(len(candidates_names)):
                    n: str = candidates_names[i]
                    p: Path = candidates_paths[i]
                    if n in close_names:
                        fuzzy.append(p)
            
        return exact, fuzzy
    
    def _display_results_to_console(self, exact: List[Path], fuzzy: List[Path], target_path: Path) -> None:
        def _fmt(p: Path) -> str:
            rel: Path
            if is_relative_to_compat(p, target_path) is True:
                rel = p.relative_to(target_path)
            else:
                rel = p
                
            icon: str
            if p.is_dir() is True:
                icon = "[DIR]"
            else:
                icon = "[FILE]"
                
            return f"  {icon} {rel}"

        if len(exact) > 0:
            logger.info(f"Exact matches for '{self.keyword}':")
            for item in exact[:20]:
                logger.info(_fmt(item))
        
        if len(fuzzy) > 0:
            logger.info(f"Potential candidates (Fuzzy matches):")
            for item in fuzzy[:10]:
                logger.info(_fmt(item))

    def _execute_interactive_deletion(self, exact: List[Path], fuzzy: List[Path], target_path: Path) -> None:
        all_to_delete: List[Path] = []
        for em in exact:
            all_to_delete.append(em)
            
        if len(fuzzy) > 0:
            logger.warning("Fuzzy matches may include unintended items!")
            if terminal.prompt_confirmation("Do you want to INCLUDE these fuzzy matches in the deletion? [y/n]: ") is True:
                for fm in fuzzy:
                    all_to_delete.append(fm)

        if len(all_to_delete) == 0:
            logger.info("No items selected for deletion. Aborting.")
            return

        if self.dry_run is True:
            logger.info(f"[DRY-RUN] Targeted: {len(all_to_delete)} items.")
            for m in all_to_delete: 
                target_str: str
                if is_relative_to_compat(m, target_path) is True:
                    target_str = str(m.relative_to(target_path))
                else:
                    target_str = m.name
                logger.info(f"  [WILL REMOVE] {target_str}")
            return

        logger.warning(f"CRITICAL: You are about to PERMANENTLY DELETE {len(all_to_delete)} items.")
        raw_input: str = input("Please type 'CONFIRM DELETE' to proceed: ")
        confirm: str = raw_input.strip()
        
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
        config.highlights = set(all_matches)
        tree_lines: List[str] = self.tree_renderer.render(result, config, root_path=target_path)
        
        tree_text: str = f"{target_path.name}/\n"
        for line in tree_lines:
            tree_text = tree_text + line + "\n"

        if format_type == 'image':
            image_renderer.render_text_to_image(tree_text, out_file, len(tree_lines))
            return

        try:
            with open(out_file, 'w', encoding='utf-8') as f:
                if format_type == 'md':
                    f.write(f"# Search Report: {self.keyword}\n\n")
                    f.write("## Visual Topology\n```text\n")
                    f.write(tree_text)
                    f.write("```\n")
                else:
                    f.write(f"Search Report: {self.keyword}\n")
                    f.write("="*40 + "\n")
                    f.write(tree_text)
                    f.write("\n")

                f.write("\n" + "="*60 + "\nMATCHED SOURCE CONTENT\n" + "="*60 + "\n\n")
                for m in all_matches:
                    if m.is_dir() is True:
                        continue
                        
                    for item in result.text_files:
                        if item.path == m:
                            content: Optional[str] = result.get_content(item, quiet=True)
                            if content is not None:
                                if format_type == 'md':
                                    fence: str = io_processor.calculate_markdown_fence(content)
                                    f.write(f"### {item.relative_path}\n")
                                    f.write(f"{fence}\n")
                                    f.write(f"{content}\n")
                                    f.write(f"{fence}\n\n")
                                else:
                                    f.write(f"--- FILE: {item.relative_path} ---\n")
                                    f.write(f"{content}\n\n")
            
            logger.info(f"Report exported: {out_file.name}")
        except OSError as err:
            raise FileSystemError(message=f"Failed to write report: {err}")