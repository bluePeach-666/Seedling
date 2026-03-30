from __future__ import annotations
from dataclasses import dataclass, field
from typing import Set, List, Optional
from pathlib import Path

@dataclass
class ScanConfig: 
    max_depth: Optional[int] = None                    
    show_hidden: bool = True
    """是否扫描隐藏文件和目录。v2.5.1 起默认为 True"""
    excludes: List[str] = field(default_factory=list)
    includes: List[str] = field(default_factory=list)
    text_only: bool = False
    file_type: Optional[str] = None
    quiet: bool = False
    highlights: Set[Path] = field(default_factory=set)
    use_regex: bool = False
    ignore_case: bool = False
    template_path: Optional[Path] = None
    """v2.5.1 提示词模板功能"""