from __future__ import annotations
from pathlib import Path
from typing import List, Dict, Any, Tuple, Set

from ....utils import logger, io_processor, terminal
from ..base import AbstractBuildPlugin

class DryRunPlugin(AbstractBuildPlugin):
    """在物理构建前进行无冲突模拟"""

    def execute(self, parsed_items: List[Dict[str, Any]], contents: Dict[str, Tuple[Path, str]], target_path: Path) -> bool:
        logger.info(f"--- [CHECK MODE] Blueprint Validation for: {target_path} ---")
        missing: Set[str] = set()
        modified: Set[str] = set()
        identical: Set[str] = set()

        for item in parsed_items:
            p: Path = item['safe_path']
            rel: str = item['safe_path'].relative_to(target_path).as_posix()
            
            if not p.exists():
                missing.add(rel)
            else:
                if not item['is_dir']:
                    if rel not in contents:
                        if io_processor.compare_file_content(p, ""):
                            modified.add(rel)
                        else:
                            identical.add(rel)
                    else:
                        identical.add(rel)
                else:
                    identical.add(rel)

        for rel, data in contents.items():
            p: Path = data[0]
            content: str = data[1]
            
            if not p.exists():
                missing.add(rel)
            else:
                if io_processor.compare_file_content(p, content):
                    modified.add(rel)
                else:
                    identical.add(rel)

        logger.info(f"  Status: {len(identical)} identical, {len(modified)} modified, {len(missing)} missing.")
        
        if modified:
            logger.warning("Mismatched Files:")
            for m in sorted(modified):
                logger.warning(f"      ~ {m}")
        
        if not missing:
            if not modified:
                logger.info("Structure is up to date. No build required.")
                return False  # 一切正常，主动阻断后续构建流程

        proceed: bool = terminal.prompt_confirmation("Proceed to build/overwrite? [y/n]: ")
        return proceed