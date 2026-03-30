from __future__ import annotations
from pathlib import Path, PureWindowsPath
from typing import List, Dict, Any, Optional, Set, Tuple

from ....core import matcher_engine
from ....utils import logger, io_processor, terminal, FileSystemError
from ..base import AbstractBlueprintParser

class TextBlueprintParser(AbstractBlueprintParser):
    def parse(self, source_file: Path, target_path: Path) -> Tuple[List[Dict[str, Any]], Dict[str, Tuple[Path, str]]]:
        resolved_target: Path = target_path.resolve()
        
        try:
            tree_lines: List[str] = io_processor.parse_directory_tree(source_file)
            file_contents: Dict[str, str] = io_processor.deserialize_fenced_blocks(source_file)
        except FileSystemError as err:
            logger.error(str(err))
            return [], {}

        raw_items: List[Dict[str, Any]] = io_processor.parse_tree_topology(tree_lines)
        
        blueprint_root_name: Optional[str] = None
        if len(raw_items) > 0:
            if 'name' in raw_items[0]:
                blueprint_root_name = raw_items[0]['name']
            
        parsed_items: List[Dict[str, Any]] = self._parse_to_safe_paths(raw_items, resolved_target)
        safe_contents: Dict[str, Tuple[Path, str]] = self._align_and_verify_contents(
            file_contents, resolved_target, blueprint_root_name, parsed_items
        )
        
        return parsed_items, safe_contents

    def _parse_to_safe_paths(self, raw_items: List[Dict[str, Any]], target_path: Path) -> List[Dict[str, Any]]:
        if len(raw_items) > 0:
            if raw_items[0]['depth'] == 0:
                has_other_roots: bool = False
                for i in range(1, len(raw_items)):
                    if raw_items[i]['depth'] == 0:
                        has_other_roots = True
                        break
                if has_other_roots is False:
                    raw_items.pop(0)

        parsed_items: List[Dict[str, Any]] = []
        stack: List[Tuple[int, Path]] = [(-1, target_path)]
        
        for item in raw_items:
            while len(stack) > 0:
                if stack[-1][0] >= item['depth']:
                    stack.pop()
                else:
                    break
            
            current_path: Path = (stack[-1][1] / item['name']).resolve()
            
            if io_processor.validate_path_security(current_path, target_path) is False:
                logger.warning(f"Security Block: {item['name']} (Path traversal detected)")
                continue

            item['safe_path'] = current_path
            parsed_items.append(item)
            
            if item['is_dir'] is True: 
                stack.append((item['depth'], current_path))
                
        return parsed_items

    def _align_and_verify_contents(
        self, 
        contents: Dict[str, str], 
        target_path: Path, 
        root_name: Optional[str],
        parsed_items: List[Dict[str, Any]]
    ) -> Dict[str, Tuple[Path, str]]:
        
        aligned_contents: Dict[str, Tuple[Path, str]] = {}
        tree_files: List[str] = []
        
        absolute_target: Path = target_path.resolve()
        
        for item in parsed_items:
            if item['is_dir'] is False:
                item_path: Path = item['safe_path'].resolve()
                rel_path_str: str = item_path.relative_to(absolute_target).as_posix()
                tree_files.append(rel_path_str)
        
        matched_tree_files: Set[str] = set()
        
        for rel_path_str, content in contents.items():
            posix_path: str = PureWindowsPath(rel_path_str).as_posix()
            clean_path: str = posix_path
            
            if root_name is not None:
                if posix_path == root_name:
                    continue
                if posix_path.startswith(f"{root_name}/"):
                    clean_path = posix_path[len(root_name) + 1:]

            best_match: Optional[str] = None

            if clean_path in tree_files:
                best_match = clean_path
            else:
                candidates: List[str] = []
                for tf in tree_files:
                    if tf.endswith(f"/{clean_path}"):
                        candidates.append(tf)
                    else:
                        if tf == clean_path:
                            candidates.append(tf)
                        
                available_candidates: List[str] = []
                for c in candidates:
                    if c not in matched_tree_files:
                        available_candidates.append(c)
                
                if len(available_candidates) > 0:
                    def _sort_len(x: str) -> int:
                        return len(x)
                    available_candidates.sort(key=_sort_len)
                    best_match = available_candidates[0]

            if best_match is None:
                available_tree_files: List[str] = []
                for tf in tree_files:
                    if tf not in matched_tree_files:
                        available_tree_files.append(tf)
                        
                close_matches: List[str] = matcher_engine.fuzzy_match_candidates(
                    target=clean_path, 
                    candidates=available_tree_files, 
                    cutoff=0.7, 
                    limit=1
                )
                
                if len(close_matches) > 0:
                    guess: str = close_matches[0]
                    
                    prefix: str = ""
                    if root_name is not None:
                        prefix = f"{root_name}/"
                    else:
                        prefix = "./"
                        
                    display_clean: str = f"{prefix}{clean_path}"
                    display_guess: str = f"{prefix}{guess}"
                    
                    prompt: str = f"Block '{display_clean}' not found in tree. Did you mean '{display_guess}'? [y/n]: "
                    if terminal.prompt_confirmation(prompt) is True:
                        best_match = guess

            if best_match is None:
                logger.warning(f"Ignored orphaned block '{rel_path_str}': Not declared in the tree blueprint.")
                continue
                
            matched_tree_files.add(best_match)
            abs_path: Path = (target_path / best_match).resolve()

            if io_processor.validate_path_security(abs_path, target_path) is False:
                raise FileSystemError(
                    message=f"Illegal file block: '{rel_path_str}'",
                    hint="This path is outside the blueprint scope."
                )
            
            aligned_contents[best_match] = (abs_path, content)
            
        return aligned_contents