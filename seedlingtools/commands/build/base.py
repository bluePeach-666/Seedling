from __future__ import annotations
from abc import ABC, abstractmethod
from pathlib import Path
from typing import List, Dict, Any, Tuple

class AbstractBlueprintParser(ABC):
    """蓝图解析器抽象基类"""
    
    @abstractmethod
    def parse(
        self, 
        source_file: Path, 
        target_path: Path
    ) -> Tuple[List[Dict[str, Any]], Dict[str, Tuple[Path, str]]]:
        pass


class AbstractBuildPlugin(ABC):
    """构建管线插件抽象基类"""
    
    @abstractmethod
    def execute(
        self, 
        parsed_items: List[Dict[str, Any]], 
        contents: Dict[str, Tuple[Path, str]], 
        target_path: Path
    ) -> bool:
        """
        执行插件逻辑。
        Returns:
            bool: 返回 True 管线继续流转。返回 False 阻断后续构建流程。
        """
        pass


class AbstractBuildExecutor(ABC):
    """物理执行器抽象基类"""
    
    @abstractmethod
    def execute(
        self, 
        parsed_items: List[Dict[str, Any]], 
        contents: Dict[str, Tuple[Path, str]], 
        target_path: Path, 
        force_mode: bool = False
    ) -> bool:
        pass