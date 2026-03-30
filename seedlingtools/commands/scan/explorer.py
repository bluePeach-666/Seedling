from __future__ import annotations
from pathlib import Path
from typing import List, Final

from .base import AbstractScanPlugin, AbstractExporter
from ...core import ScanConfig, TraversalResult
from ...utils import logger

class ScanOrchestrator:
    def __init__(self, exporter: AbstractExporter) -> None:
        self._exporter: Final[AbstractExporter] = exporter
        self._plugins: List[AbstractScanPlugin] = []

    def add_plugin(self, plugin: AbstractScanPlugin) -> None:
        self._plugins.append(plugin)

    def run_pipeline(
        self, 
        target_path: Path, 
        config: ScanConfig, 
        result: TraversalResult, 
        out_file: Path, 
        is_full: bool = False
    ) -> None:
        if len(self._plugins) > 0:
            for plugin in self._plugins:
                plugin_name: str = plugin.__class__.__name__
                logger.debug(f"Running plugin: {plugin_name}")
                plugin.execute(target_path, config, result, out_file=out_file, is_full=is_full)
            return

        success: bool = self._exporter.export(
            target_path, 
            config, 
            result, 
            out_file, 
            is_full
        )

        if success is True:
            logger.info(f"Task completed. Results saved to: {out_file}")