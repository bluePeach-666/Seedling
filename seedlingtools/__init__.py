"""
Seedling-tools  
A high-performance CLI toolkit designed for codebase exploration, intelligent analysis, and LLM context aggregation.  
Copyright (c) 2026 Kaelen Chow. All rights reserved.  
版权所有 © 2026 周珈民。保留一切权利。
"""

from __future__ import annotations
from .main import scan, build
from .commands.build import (
    BuildOrchestrator,
    TextBlueprintParser,
    LocalFSExecutor,
    DryRunPlugin,
    setup_build_parser,
    handle_build,
)
from .commands.scan import (
    ScanOrchestrator, 
    AbstractScanPlugin, 
    AbstractExporter,
    TextExporter, 
    JsonExporter, 
    AnalyzerPlugin, 
    GrepPlugin, 
    SearchPlugin, 
    SkeletonPlugin,
    setup_scan_parser,
    handle_scan
)
from .core import (
    ScanConfig, 
    TraversalResult, 
    TraversalItem
)
from .utils import (
    get_package_version,
    AbstractLogger, 
    AbstractTerminal,
    AbstractIOProcessor,
    AbstractImageRenderer, 
    logger,
    terminal,
    io_processor,
    image_renderer
)

__version__ = get_package_version()
__author__ = "周珈民 (Kaelen Chow)"
__name__ = "Seedling-tools"

__all__ = [
    "__version__", 
    "__author__", 
    "__name__",
    "scan", 
    "build",
    "ScanConfig", 
    "TraversalResult", 
    "TraversalItem",
    "ScanOrchestrator", 
    "setup_scan_parser",
    "handle_scan",
    "BuildOrchestrator",
    "TextBlueprintParser",
    "LocalFSExecutor",
    "DryRunPlugin",
    "setup_build_parser",
    "handle_build",
    "AbstractScanPlugin", 
    "AbstractExporter",
    "TextExporter", 
    "JsonExporter",
    "AnalyzerPlugin", 
    "GrepPlugin", 
    "SearchPlugin", 
    "SkeletonPlugin",
    "AbstractLogger",
    "AbstractTerminal",
    "AbstractIOProcessor",
    "AbstractImageRenderer",
    "logger",
    "terminal",
    "io_processor",
    "image_renderer"
]