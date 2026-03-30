# Unit tests for Seedling-tools v2.5.
# Copyright (c) 2026 Kaelen Chow. All rights reserved.

from __future__ import annotations
import sys
import pytest #type: ignore
from typing import Final

from seedlingtools.commands.scan.plugins.skeleton import SkeletonPlugin

def _is_python_version_compatible() -> bool:
    """
    Check if the current runtime satisfies the Python 3.9+ requirement.
    """
    major: int = sys.version_info[0]
    minor: int = sys.version_info[1]
    
    if major > 3:
        return True
    
    if major == 3:
        if minor >= 9:
            return True
            
    return False

@pytest.mark.skipif(
    _is_python_version_compatible() is False, 
    reason="Skeleton extraction requires Python 3.9 or higher for ast.unparse support"
)
def test_skeleton_ast_extraction() -> None:
    """
    Verify the AST transformation logic: stripping bodies while preserving docstrings.
    """
    source_code: Final[str] = """
def calculate(a, b):
    \"\"\"Docstring content\"\"\"
    res = a + b
    return res

class MyClass:
    def method(self):
        print("this should be hidden")
"""
    plugin: SkeletonPlugin = SkeletonPlugin()
    # Execute internal extraction logic
    skeleton: str = plugin._extract_skeleton(source_code)
    
    # Assert structural integrity
    assert "def calculate(a, b):" in skeleton
    assert "class MyClass:" in skeleton
    
    # Assert body stripping logic
    assert "Docstring content" in skeleton
    assert "..." in skeleton
    
    # Ensure sensitive implementation details are removed
    assert "res = a + b" not in skeleton
    assert "print" not in skeleton