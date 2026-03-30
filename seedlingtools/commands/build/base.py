from __future__ import annotations
from abc import ABC, abstractmethod
from pathlib import Path
from typing import List, Dict, Any, Tuple

class AbstractBlueprintParser(ABC):
    @abstractmethod
    def parse(
        self, 
        source_file: Path, 
        target_path: Path
    ) -> Tuple[List[Dict[str, Any]], Dict[str, Tuple[Path, str]]]:
        pass


class AbstractBuildPlugin(ABC):
    @abstractmethod
    def execute(
        self, 
        parsed_items: List[Dict[str, Any]], 
        contents: Dict[str, Tuple[Path, str]], 
        target_path: Path
    ) -> bool:
        pass


class AbstractBuildExecutor(ABC):
    @abstractmethod
    def execute(
        self, 
        parsed_items: List[Dict[str, Any]], 
        contents: Dict[str, Tuple[Path, str]], 
        target_path: Path, 
        force_mode: bool = False
    ) -> bool:
        pass