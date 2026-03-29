from __future__ import annotations
from pathlib import Path
from typing import List, Final

from ...utils import logger
from .base import AbstractBlueprintParser, AbstractBuildPlugin, AbstractBuildExecutor

class BuildOrchestrator:
    """构建管线编排引擎"""

    def __init__(self, parser: AbstractBlueprintParser, executor: AbstractBuildExecutor) -> None:
        self._parser: Final[AbstractBlueprintParser] = parser
        self._executor: Final[AbstractBuildExecutor] = executor
        self._plugins: List[AbstractBuildPlugin] = []

    def add_plugin(self, plugin: AbstractBuildPlugin) -> None:
        """挂载构建管线插件"""
        self._plugins.append(plugin)

    def run_pipeline(self, source_file: Path, target_dir: Path, force_mode: bool = False) -> bool:
        """调度并执行完整的蓝图构建生命周期"""
        target_path: Path = target_dir.resolve(strict=False)
        
        # 解析蓝图
        parsed_items, contents = self._parser.parse(source_file, target_path)
        if not parsed_items:
            if not contents:
                logger.error(f"Pipeline aborted: No valid structures found in '{source_file.name}'.")
                return False

        # 插件拦截与预检
        if self._plugins:
            for plugin in self._plugins:
                should_continue: bool = plugin.execute(parsed_items, contents, target_path)
                if not should_continue:
                    return True  # 插件主动阻断

        # 物理写入执行
        return self._executor.execute(parsed_items, contents, target_path, force_mode)