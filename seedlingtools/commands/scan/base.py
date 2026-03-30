from __future__ import annotations
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

from ...core import ScanConfig, TraversalResult

class AbstractScanPlugin(ABC):
    @abstractmethod
    def execute(
        self, 
        target_path: Path, 
        config: ScanConfig, 
        result: TraversalResult, 
        **kwargs: Any
    ) -> None:
        pass

class AbstractExporter(ABC):
    @abstractmethod
    def export(
        self, 
        target_path: Path, 
        config: ScanConfig, 
        result: TraversalResult, 
        out_file: Path, 
        is_full: bool = False
    ) -> bool:
        pass