from __future__ import annotations
from pathlib import Path
from typing import List, Dict, Any, Tuple, Set

from ....utils import logger, io_processor, terminal
from ..base import AbstractBuildPlugin

class DryRunPlugin(AbstractBuildPlugin):
    def execute(self, parsed_items: List[Dict[str, Any]], contents: Dict[str, Tuple[Path, str]], target_path: Path) -> bool:
        logger.info(f"--- [CHECK MODE] Blueprint Validation for: {target_path} ---")
        missing: Set[str] = set()
        modified: Set[str] = set()
        identical: Set[str] = set()

        for item in parsed_items:
            p: Path = item['safe_path']
            rel: str = item['safe_path'].relative_to(target_path).as_posix()
            
            if p.exists() is False:
                missing.add(rel)
            else:
                if item['is_dir'] is False:
                    if rel not in contents:
                        if io_processor.compare_file_content(p, "") is True:
                            modified.add(rel)
                        else:
                            identical.add(rel)
                    else:
                        identical.add(rel)
                else:
                    identical.add(rel)

        for rel, data in contents.items():
            p_content: Path = data[0]
            content_str: str = data[1]
            
            if p_content.exists() is False:
                missing.add(rel)
            else:
                if io_processor.compare_file_content(p_content, content_str) is True:
                    modified.add(rel)
                else:
                    identical.add(rel)

        logger.info(f"  Status: {len(identical)} identical, {len(modified)} modified, {len(missing)} missing.")
        
        if len(modified) > 0:
            logger.warning("Mismatched Files:")
            sorted_modified: List[str] = sorted(list(modified))
            for m in sorted_modified:
                logger.warning(f"      ~ {m}")
        
        if len(missing) == 0:
            if len(modified) == 0:
                logger.info("Structure is up to date. No build required.")
                return False

        prompt_text: str = "Proceed to build/overwrite? [y/n]: "
        proceed: bool = terminal.prompt_confirmation(prompt_text)
        
        return proceed