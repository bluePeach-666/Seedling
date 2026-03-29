from __future__ import annotations
from pathlib import Path
from typing import List, Dict, Any, Tuple, Set

from ....utils import logger, io_processor, terminal
from ..base import AbstractBuildExecutor

class LocalFSExecutor(AbstractBuildExecutor):
    """本地文件系统物理构建执行器"""

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
                if item['is_dir']:
                    if not path.exists():
                        path.mkdir(parents=True, exist_ok=True)
                        dirs_cnt += 1
                        logger.info(f"  Created [DIR]  : {rel}")
                    else:
                        skipped += 1
                else:
                    content: str = ""
                    if rel in contents:
                        content = contents[rel][1]
                        
                    if path.exists():
                        if io_processor.compare_file_content(path, content):
                            pending.append((rel, path, content))
                        else:
                            skipped += 1
                    else:
                        io_processor.write_text_safely(path, content)
                        files_cnt += 1
                        logger.info(f"  Restored [FILE] : {rel}")
            except OSError as e:
                logger.error(f"Error at {rel}: {e}")

        for rel, data in contents.items():
            path: Path = data[0]
            content: str = data[1]
            
            if rel not in handled:
                if path.exists():
                    if io_processor.compare_file_content(path, content):
                        pending.append((rel, path, content))
                    else:
                        skipped += 1
                else:
                    io_processor.write_text_safely(path, content)
                    files_cnt += 1
                    logger.info(f"  Restored [FILE*]: {rel}")

        if pending:
            logger.info("\n" + "-" * 20 + " Overwrite Check " + "-" * 20)
            for rel, path, content in pending:
                if force_mode:
                    io_processor.write_text_safely(path, content)
                    files_cnt += 1
                    logger.info(f"  Updated [FILE] : {rel}")
                else:
                    prompt: str = f"Overwrite '{rel}'? [y/n]: "
                    if terminal.prompt_confirmation(prompt, default_no=True):
                        io_processor.write_text_safely(path, content)
                        files_cnt += 1
                        logger.info(f"  Updated [FILE] : {rel}")
                    else:
                        skipped += 1

        logger.info("\n" + "=" * 40)
        logger.info(f"SUCCESS: {dirs_cnt} dirs, {files_cnt} files. {skipped} skipped.")
        return True