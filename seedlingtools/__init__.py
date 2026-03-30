"""
Seedling-tools  
A high-performance CLI toolkit designed for codebase exploration, intelligent analysis, and LLM context aggregation.  
Copyright (c) 2026 Kaelen Chow. All rights reserved.  
"""

from __future__ import annotations
from .main import scan, build
from .core import ScanConfig, TraversalResult, TraversalItem
from .utils import get_package_version

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
    "TraversalItem"
]