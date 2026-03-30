from __future__ import annotations
from pathlib import Path
from typing import List, Dict, Any, Tuple, Set

from ....utils import logger, io_processor, terminal
from ..base import AbstractBuildExecutor

class LocalFSExecutor(AbstractBuildExecutor):
    def execute(self, parsed_items: List[Dict[str, Any]], contents: Dict[str, Tuple[Path, str]], target_path: Path, force_mode: bool = False) -> bool:
        logger.info(f"Initializing build engine at: {target_path}")
        dirs_cnt: int = 0
        files_cnt: int = 0
        skipped: int = 0
        pending: List[Tuple[str, Path, str]] = []

        handled: Set[str] = set()
        
        for item in parsed_items:
            path: Path = item['safe_path']
            rel: str = item['safe_path'].relative_to(target_path).as_posix()
            handled.add(rel)
            
            try:
                if item['is_dir'] is True:
                    if path.exists() is False:
                        path.mkdir(parents=True, exist_ok=True)
                        dirs_cnt += 1
                        logger.info(f"  Created [DIR]  : {rel}")
                    else:
                        skipped += 1
                else:
                    content: str = ""
                    if rel in contents:
                        content = contents[rel][1]
                        
                    if path.exists() is True:
                        if io_processor.compare_file_content(path, content) is True:
                            pending.append((rel, path, content))
                        else:
                            skipped += 1
                    else:
                        io_processor.write_text_safely(path, content)
                        files_cnt += 1
                        logger.info(f"  Restored [FILE] : {rel}")
            except OSError as err:
                logger.error(f"Error at {rel}: {err}")

        for rel, data in contents.items():
            path_content: Path = data[0]
            content_str: str = data[1]
            
            if rel not in handled:
                if path_content.exists() is True:
                    if io_processor.compare_file_content(path_content, content_str) is True:
                        pending.append((rel, path_content, content_str))
                    else:
                        skipped += 1
                else:
                    io_processor.write_text_safely(path_content, content_str)
                    files_cnt += 1
                    logger.info(f"  Restored [FILE*]: {rel}")

        if len(pending) > 0:
            logger.info("\n" + "-" * 20 + " Overwrite Check " + "-" * 20)
            for pending_item in pending:
                rel_pending: str = pending_item[0]
                path_pending: Path = pending_item[1]
                content_pending: str = pending_item[2]
                
                if force_mode is True:
                    io_processor.write_text_safely(path_pending, content_pending)
                    files_cnt += 1
                    logger.info(f"  Updated [FILE] : {rel_pending}")
                else:
                    prompt: str = f"Overwrite '{rel_pending}'? [y/n]: "
                    if terminal.prompt_confirmation(prompt, default_no=True) is True:
                        io_processor.write_text_safely(path_pending, content_pending)
                        files_cnt += 1
                        logger.info(f"  Updated [FILE] : {rel_pending}")
                    else:
                        skipped += 1

        logger.info("\n" + "=" * 40)
        logger.info(f"SUCCESS: {dirs_cnt} dirs, {files_cnt} files. {skipped} skipped.")
        
        return True