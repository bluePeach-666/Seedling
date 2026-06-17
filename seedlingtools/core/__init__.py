"""
The core business logic and traversal engine of the Seedling-tools.
Copyright (c) 2026 Kaelen Chow. All rights reserved.
"""

from __future__ import annotations
from .comment_stripper import CommentStripper, StripCommentsResult
from .config import BuildConfig, CleanConfig, ScanConfig
from .config_manager import (
    AbstractConfigManager,
    SeedlingConfigManager,
    config_manager
)
from .patterns import (
    AbstractMatcherEngine,
    CoreMatcherEngine,
    matcher_engine
)
from .traversal import (
    TraversalItem,
    TraversalResult,
    AbstractTraverser,
    AbstractTreeRenderer,
    DepthFirstTraverser,
    StandardTreeRenderer
)

__all__ = [
    "CommentStripper",
    "StripCommentsResult",
    "BuildConfig",
    "CleanConfig",
    "ScanConfig",
    "AbstractConfigManager",
    "SeedlingConfigManager",
    "config_manager",
    "AbstractMatcherEngine",
    "CoreMatcherEngine",
    "matcher_engine",
    "TraversalItem",
    "TraversalResult",
    "AbstractTraverser",
    "AbstractTreeRenderer",
    "DepthFirstTraverser",
    "StandardTreeRenderer"
]
