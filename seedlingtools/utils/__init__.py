"""
The underlying tool chain and infrastructure of the Seedling-tools.  
Copyright (c) 2026 Kaelen Chow. All rights reserved.  
"""

from __future__ import annotations
from .exceptions import (
    SeedlingToolsError,
    SystemProbeError,
    FileSystemError,
    ConfigurationError
)
from .constants import FileSettings
from .patterns import SingletonMeta
from .sysinfo import (
    get_package_version,
    get_recursion_limit,
    get_memory_limit_mb,
    is_relative_to_compat
)
from .log_helper import AbstractLogger, logger
from .term_helper import AbstractTerminal, terminal
from .io_helper import AbstractIOProcessor, io_processor
from .image_helper import AbstractImageRenderer, image_renderer
from .git_helper import AbstractGitHelper, gitter

__all__ = [
    "SeedlingToolsError",
    "SystemProbeError",
    "FileSystemError",
    "ConfigurationError",
    "FileSettings",
    "get_package_version",
    "get_recursion_limit",
    "get_memory_limit_mb",
    "is_relative_to_compat",
    "AbstractLogger",
    "AbstractTerminal",
    "AbstractIOProcessor",
    "AbstractImageRenderer",
    "AbstractGitHelper",
    "logger",
    "terminal",
    "io_processor",
    "image_renderer",
    "gitter",
    "SingletonMeta"
]