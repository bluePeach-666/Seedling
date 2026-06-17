from __future__ import annotations
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Set


@dataclass
class ScanConfig:
    max_depth: Optional[int] = None
    show_hidden: bool = True
    excludes: List[str] = field(default_factory=list)
    includes: List[str] = field(default_factory=list)
    text_only: bool = False
    file_type: Optional[str] = None
    quiet: bool = False
    highlights: Set[Path] = field(default_factory=set)
    use_regex: bool = False
    ignore_case: bool = False
    template_path: Optional[Path] = None
    strip_comments: bool = False


@dataclass
class BuildConfig:
    default_target: Optional[Path] = None
    force: bool = False
    check: bool = False
    direct: bool = False
    allow_overwrite: bool = False


@dataclass
class CleanConfig:
    strategy: str = "python-standard"
    dry_run_default: bool = False
    recursive_dirs: List[str] = field(default_factory=lambda: [
        "__pycache__",
        ".pytest_cache",
        ".mypy_cache",
        ".ruff_cache",
        ".tox",
        ".nox"
    ])
    root_only_dirs: List[str] = field(default_factory=lambda: ["build", "dist"])
    extensions: List[str] = field(default_factory=lambda: [".pyc", ".pyo", ".pyd"])
    ignore_dirs: List[str] = field(default_factory=lambda: [
        ".git",
        ".venv",
        "venv",
        "env",
        ".env",
        "node_modules"
    ])
    custom_targets: List[str] = field(default_factory=list)
    external_script: Optional[Path] = None
    external_mode: str = "candidates-only"
