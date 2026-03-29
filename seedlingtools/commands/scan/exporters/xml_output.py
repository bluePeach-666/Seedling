from __future__ import annotations
from pathlib import Path
from typing import List
from ..base import AbstractExporter
from ....core import ScanConfig, TraversalResult, StandardTreeRenderer
from ....utils import image_renderer, io_processor, FileSystemError, terminal, logger, SeedlingToolsError

class XmlExporter(AbstractExporter):
    """XML 格式化导出适配器 (v2.5.1 计划实现)"""

    def export(self, target_path: Path, config: ScanConfig, result: TraversalResult, out_file: Path, is_full: bool = False) -> bool:
        raise SeedlingToolsError(
            message="XML export format is scheduled for v2.5.1.",
            hint="Please use 'md', 'json' or 'txt' for now. Check back soon!"
        )