"""
Configuration classes and constants for Seedling scanning engine.
"""
from dataclasses import dataclass, field
from typing import Set, List, Optional
from pathlib import Path

from .sysinfo import get_system_depth_limit


# --- Core Constraint Constants ---
MAX_FILE_SIZE = 2 * 1024 * 1024  # 2MB disk limit
MAX_ITERATION_DEPTH = 1000       # Explicit traversal hard limit
HARD_DEPTH_LIMIT = min(get_system_depth_limit(), MAX_ITERATION_DEPTH)

SPECIAL_TEXT_NAMES = {'makefile', 'dockerfile', 'license', 'caddyfile', 'procfile'}

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

# File type mapping for --type filtering
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
    'all': None  # Special case - matches all
}


@dataclass
class ScanConfig:
    """Encapsulates all configuration options for the scanning engine."""
    max_depth: Optional[int] = None
    show_hidden: bool = False
    excludes: List[str] = field(default_factory=list)
    includes: List[str] = field(default_factory=list)  # Include patterns
    text_only: bool = False
    file_type: Optional[str] = None  # File type filter
    quiet: bool = False
    highlights: Set[Path] = field(default_factory=set)
    use_regex: bool = False  # Regex mode for search
    ignore_case: bool = False  # Case sensitivity for grep/search
