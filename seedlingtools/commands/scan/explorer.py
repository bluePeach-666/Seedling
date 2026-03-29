from __future__ import annotations
from pathlib import Path
from typing import List, Final

from .base import AbstractScanPlugin, AbstractExporter
from ...core import ScanConfig, TraversalResult
from ...utils import logger

class ScanOrchestrator:
    """扫描编排器，负责将不同的插件和导出器组合在一起执行"""

    def __init__(self, exporter: AbstractExporter) -> None:
        self._exporter: Final[AbstractExporter] = exporter
        self._plugins: List[AbstractScanPlugin] = []

    def add_plugin(self, plugin: AbstractScanPlugin) -> None:
        """注册一个分析插件"""
        self._plugins.append(plugin)

    def run_pipeline(
        self, 
        target_path: Path, 
        config: ScanConfig, 
        result: TraversalResult, 
        out_file: Path, 
        is_full: bool = False
    ) -> None:
        """
        - 如果存在特殊插件，交由插件全权接管生命周期。
        - 仅在普通扫描模式下，执行默认的数据导出。
        """
        if self._plugins:
            for plugin in self._plugins:
                logger.debug(f"Running plugin: {plugin.__class__.__name__}")
                plugin.execute(target_path, config, result, out_file=out_file, is_full=is_full)
            return

        success = self._exporter.export(
            target_path, 
            config, 
            result, 
            out_file, 
            is_full
        )

        if success:
            logger.info(f"Task completed. Results saved to: {out_file}")