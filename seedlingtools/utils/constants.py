from __future__ import annotations
from dataclasses import dataclass, field
from typing import Final, FrozenSet, Dict, Tuple, List, Optional, Any
from .sysinfo import get_recursion_limit

@dataclass(frozen=True)
class _FileConstants:
    PROBE_CHUNK_SIZE: Final[int] = 1024
    MAX_FILE_SIZE: Final[int] = 2 * 1024 * 1024
    
    HARD_DEPTH_LIMIT: Final[int] = field(
        default_factory=lambda: min(get_recursion_limit(), 1000)
    )
    
    BINARY_SIGNATURES: Final[Tuple[bytes, ...]] = (
        b'\x89PNG', b'GIF89a', b'GIF87a', b'\xff\xd8\xff',
        b'MZ', b'\x7fELF', b'PK\x03\x04', b'%PDF-', b'Rar!\x1a\x07'
    )
    
    SPECIAL_TEXT_NAMES: Final[FrozenSet[str]] = frozenset({
        'makefile', 'dockerfile', 'license', 'caddyfile', 'procfile'
    })
    
    TEXT_EXTENSIONS: Final[FrozenSet[str]] = frozenset({
        '.c', '.h', '.cpp', '.cc', '.cxx', '.c++', '.cp',
        '.hpp', '.hxx', '.h++', '.hh', '.inc', '.inl',
        '.cu', '.cuh',
        '.py', '.js', '.ts', '.java', '.go', '.rs', '.cs',
        '.html', '.css', '.md', '.txt',
        '.json', '.yaml', '.yml', '.toml', '.xml',
        '.ini', '.cfg', '.csv',
        '.sh', '.bat', '.ps1', '.sql'
    })
    
    FILE_TYPE_MAP: Final[Dict[str, Optional[FrozenSet[str]]]] = field(
        default_factory=lambda: {
            'py': frozenset({'.py', '.pyw', '.pyi'}),
            'js': frozenset({'.js', '.mjs', '.cjs','.jsx'}),
            'ts': frozenset({'.ts', '.tsx'}),
            'cpp': frozenset({'.c', '.h', '.cpp', '.hpp', '.cc', '.cxx'}),
            'go': frozenset({'.go'}),
            'java': frozenset({'.java'}),
            'rs': frozenset({'.rs'}),
            'web': frozenset({'.html', '.css', '.scss', '.vue', '.svelte'}),
            'json': frozenset({'.json'}),
            'yaml': frozenset({'.yaml', '.yml'}),
            'md': frozenset({'.md', '.markdown'}),
            'shell': frozenset({'.sh', '.bash', '.zsh'}),
            'all': None
        }
    )
    
    PROJECT_SIGNATURES: Final[Dict[str, Dict[str, Any]]] = field(
        default_factory=lambda: {
            'python': {'files': ['pyproject.toml', 'setup.py', 'requirements.txt', 'setup.cfg', 'Pipfile'], 'ext': {'.py', '.pyw', '.pyi'}},
            'node': {'files': ['package.json', 'yarn.lock', 'pnpm-lock.yaml'], 'ext': {'.js', '.ts', '.jsx', '.tsx', '.mjs', '.cjs'}},
            'go': {'files': ['go.mod', 'go.sum'], 'ext': {'.go'}},
            'rust': {'files': ['Cargo.toml', 'Cargo.lock'], 'ext': {'.rs'}},
            'java': {'files': ['pom.xml', 'build.gradle', 'build.gradle.kts'], 'ext': {'.java', '.kt', '.kts'}},
            'cpp': {'files': ['CMakeLists.txt', 'Makefile', 'meson.build'], 'ext': {'.cpp', '.h', '.cc', '.hpp', '.cxx'}}
        }
    )
    
    ENTRY_PATTERNS: Final[Dict[str, List[str]]] = field(
        default_factory=lambda: {
            'python': [r'if\s+__name__\s*==\s*["\']__main__["\']', r'def\s+main\s*\('],
            'node': [r'export\s+default', r'express\(\)', r'export\s+function', r'app\.listen'],
            'go': [r'func\s+main\s*\(\)'],
            'rust': [r'fn\s+main\s*\(\)'],
            'java': [r'public\s+static\s+void\s+main'],
            'cpp': [r'int\s+main\s*\(']
        }
    )
    
    GARBAGE_PATTERNS: Final[List[str]] = field(
        default_factory=lambda: [
            "__pycache__", ".DS_Store", "node_modules", ".venv", "venv", 
            ".pytest_cache", ".idea", ".vscode", "target", "build", "dist"
        ]
    )

FileSettings: Final[_FileConstants] = _FileConstants()