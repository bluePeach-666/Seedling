from __future__ import annotations
from pathlib import Path
from typing import List, Final, Dict, Any, Tuple

from ...utils import logger
from .base import AbstractBlueprintParser, AbstractBuildPlugin, AbstractBuildExecutor

class BuildOrchestrator:
    def __init__(self, parser: AbstractBlueprintParser, executor: AbstractBuildExecutor) -> None:
        self._parser: Final[AbstractBlueprintParser] = parser
        self._executor: Final[AbstractBuildExecutor] = executor
        self._plugins: List[AbstractBuildPlugin] = []

    def add_plugin(self, plugin: AbstractBuildPlugin) -> None:
        self._plugins.append(plugin)

    def run_pipeline(self, source_file: Path, target_dir: Path, force_mode: bool = False) -> bool:
        target_path: Path = target_dir.resolve(strict=False)
        
        parsed_result: Tuple[List[Dict[str, Any]], Dict[str, Tuple[Path, str]]] = self._parser.parse(source_file, target_path)
        parsed_items: List[Dict[str, Any]] = parsed_result[0]
        contents: Dict[str, Tuple[Path, str]] = parsed_result[1]
        
        if len(parsed_items) == 0:
            if len(contents) == 0:
                logger.error(f"Pipeline aborted: No valid structures or file blocks found in '{source_file.name}'.")
                return False

        if len(self._plugins) > 0:
            logger.debug(f"Executing {len(self._plugins)} build plugins...")
            for plugin in self._plugins:
                plugin_name: str = plugin.__class__.__name__
                should_continue: bool = plugin.execute(parsed_items, contents, target_path)
                
                if should_continue is False:
                    logger.warning(f"Pipeline Interrupted: Plugin '{plugin_name}' aborted the build process.")
                    return True

        logger.info(f"Executing physical build to: {target_path}")
        
        execution_result: bool = self._executor.execute(
            parsed_items=parsed_items, 
            contents=contents, 
            target_path=target_path, 
            force_mode=force_mode
        )
        
        if execution_result is True:
            logger.info("Build lifecycle completed successfully.")
        else:
            logger.error("Build lifecycle failed during physical execution.")
            
        return execution_result