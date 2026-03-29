from dataclasses import dataclass, field
from typing import Set, List, Optional
from pathlib import Path

@dataclass
class ScanConfig: 
    """扫描配置类，包含所有扫描相关的参数设置"""

    max_depth: Optional[int] = None                    
    """扫描的最大深度，默认不限制"""

    show_hidden: bool = False
    """是否扫描隐藏文件和目录，默认不扫描"""

    excludes: List[str] = field(default_factory=list)
    """排除路径列表，默认不排除任何路径"""

    includes: List[str] = field(default_factory=list)
    """白名单列表，默认不优先扫描任何路径"""

    text_only: bool = False
    """扫描是否仅限于被识别为文本文件的文件，默认扫描所有文件类型"""

    file_type: Optional[str] = None
    """是否仅扫描某一单一类型的文件，默认不进行类型过滤"""

    quiet: bool = False
    """是否静默输出，默认输出扫描过程中的日志信息"""

    highlights: Set[Path] = field(default_factory=set)
    """高亮显示的路径集合，默认为空"""

    use_regex: bool = False
    """是否使用正则表达式进行路径过滤和白名单匹配，默认使用简单的字符串匹配"""

    ignore_case: bool = False
    """是否忽略路径过滤和白名单匹配中的大小写，默认区分大小写"""

    template_path: Optional[Path] = None
    """预留给 v2.5.1 的提示词模板功能，目前不启用"""
