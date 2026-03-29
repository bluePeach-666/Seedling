import sys
import pytest #type: ignore
from seedlingtools import SkeletonPlugin

@pytest.mark.skipif(sys.version_info < (3, 9), reason="requires python3.9 or higher")
def test_skeleton_ast_extraction():
    source_code = """
def calculate(a, b):
    \"\"\"Docstring\"\"\"
    res = a + b
    return res

class MyClass:
    def method(self):
        print("hidden")
"""
    plugin = SkeletonPlugin()
    skeleton = plugin._extract_skeleton(source_code)
    
    assert "def calculate(a, b):" in skeleton
    assert "Docstring" in skeleton
    assert "..." in skeleton
    assert "print" not in skeleton
    assert "class MyClass:" in skeleton
