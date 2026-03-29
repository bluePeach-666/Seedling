from __future__ import annotations
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any
from ...core import ScanConfig, TraversalResult

class AbstractScanPlugin(ABC):
    """扫描分析插件策略的抽象基类"""
    
    @abstractmethod
    def execute(self, target_path: Path, config: ScanConfig, result: TraversalResult, **kwargs: Any) -> None:
        """执行具体的扫描后置分析或处理逻辑"""
        pass


class AbstractExporter(ABC):
    """数据导出适配器策略的抽象基类"""
    
    @abstractmethod
    def export(self, target_path: Path, config: ScanConfig, result: TraversalResult, out_file: Path, is_full: bool = False) -> bool:
        """将遍历结果序列化并导出为特定格式"""
        pass