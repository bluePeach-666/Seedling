import pytest #type: ignore
import os
from seedlingtools import ScanConfig
from seedlingtools.core import DepthFirstTraverser

def test_circular_symlink_protection(tmp_path):
    traverser = DepthFirstTraverser()
    config = ScanConfig()
    
    dir_a = tmp_path / "dir_a"
    dir_a.mkdir()
    try:
        os.symlink(dir_a, dir_a / "recursive_link")
        result = traverser.traverse(tmp_path, config)
        assert result.stats["dirs"] == 2
    except OSError:
        pytest.skip("Symlinks not supported on this platform")

def test_max_depth_enforcement(tmp_path):
    curr = tmp_path
    for i in range(5):
        curr = curr / f"level_{i}"
        curr.mkdir()
        
    config = ScanConfig(max_depth=2)
    result = DepthFirstTraverser().traverse(tmp_path, config)
    
    assert result.stats["dirs"] == 2