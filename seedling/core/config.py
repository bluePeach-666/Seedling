from dataclasses import dataclass, field
from typing import Set, List, Optional
from pathlib import Path
from .sysinfo import get_system_depth_limit

# 约束常量
MAX_FILE_SIZE = 2 * 1024 * 1024  # 硬盘文件读取上限
MAX_ITERATION_DEPTH = 1000       # 目录遍历绝对深度
HARD_DEPTH_LIMIT = min(get_system_depth_limit(), MAX_ITERATION_DEPTH) # 动态深度限制

# 文件名白名单
SPECIAL_TEXT_NAMES = {'makefile', 'dockerfile', 'license', 'caddyfile', 'procfile'}

# 扩展名
TEXT_EXTENSIONS = {
    '.c', '.h', '.cpp', '.cc', '.cxx', '.c++', '.cp',
    '.hpp', '.hxx', '.h++', '.hh', '.inc', '.inl',
    '.cu', '.cuh',
    '.py', '.js', '.ts', '.java', '.go', '.rs', '.cs',
    '.html', '.css', '.md', '.txt',
    '.json', '.yaml', '.yml', '.toml', '.xml',
    '.ini', '.cfg', '.csv',
    '.sh', '.bat', '.ps1', '.sql'
}

# 参数映射MAP
FILE_TYPE_MAP = {
    'py': {'.py', '.pyw', '.pyi'},
    'js': {'.js', '.mjs', '.cjs', '.jsx'},
    'ts': {'.ts', '.tsx'},
    'cpp': {'.c', '.h', '.cpp', '.hpp', '.cc', '.cxx'},
    'go': {'.go'},
    'java': {'.java'},
    'rs': {'.rs'},
    'web': {'.html', '.css', '.scss', '.vue', '.svelte'},
    'json': {'.json'},
    'yaml': {'.yaml', '.yml'},
    'md': {'.md', '.markdown'},
    'shell': {'.sh', '.bash', '.zsh'},
    'all': None  # 跳过类型过滤，匹配所有文件
}

@dataclass
class ScanConfig: 
    """全局配置数据类"""
    max_depth: Optional[int] = None                    # 指定深度限制
    show_hidden: bool = False                          # 隐藏文件目录
    excludes: List[str] = field(default_factory=list)  # 路径过滤
    includes: List[str] = field(default_factory=list)  # 白名单
    text_only: bool = False                            # 严格文本
    file_type: Optional[str] = None                    # 单语言文件类型过滤
    quiet: bool = False                                # 静默模式
    highlights: Set[Path] = field(default_factory=set) # 高亮显示
    use_regex: bool = False                            # 搜索正则
    ignore_case: bool = False                          # 忽略大小写
