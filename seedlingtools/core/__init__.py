"""
The core business logic and traversal engine of the Seedling-tools.  
Copyright (c) 2026 Kaelen Chow. All rights reserved.  
版权所有 © 2026 周珈民。保留一切权利。
"""

from __future__ import annotations
from .config import ScanConfig
from .patterns import (
    evaluate_exclusion_rules,
    evaluate_inclusion_rules,
    validate_scan_target,
    fuzzy_match_candidates,
    evaluate_regex_rule,
    evaluate_exact_rule,
    detect_text_file,
    probe_binary_signature
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
    "ScanConfig",
    "detect_text_file",
    "probe_binary_signature",
    "evaluate_exclusion_rules",
    "evaluate_inclusion_rules",
    "validate_scan_target",
    "fuzzy_match_candidates",
    "evaluate_regex_rule",
    "evaluate_exact_rule",
    "TraversalItem",
    "TraversalResult",
    "AbstractTraverser",
    "AbstractTreeRenderer",
    "DepthFirstTraverser",
    "StandardTreeRenderer"
]