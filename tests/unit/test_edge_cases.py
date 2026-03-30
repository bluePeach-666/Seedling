# Unit tests for Seedling-tools v2.5.
# Copyright (c) 2026 Kaelen Chow. All rights reserved.

from __future__ import annotations
import os
import pytest #type: ignore
from pathlib import Path
from unittest.mock import patch, MagicMock
from typing import Final, List

from seedlingtools.utils.sysinfo import get_memory_limit_mb, _MEM_FALLBACK_MB
from seedlingtools.utils.exceptions import SystemProbeError
from seedlingtools.core.config import ScanConfig
from seedlingtools.core.traversal import DepthFirstTraverser, TraversalResult

def test_circular_symlink_protection(tmp_path: Path) -> None:
    """
    Verify that the traversal engine correctly identifies and skips circular symlinks
    to prevent infinite recursion.
    """
    traverser: DepthFirstTraverser = DepthFirstTraverser()
    config: ScanConfig = ScanConfig()
    
    dir_a: Path = tmp_path / "dir_a"
    dir_a.mkdir()
    
    try:
        # Create a symbolic link pointing back to its parent
        link_path: Path = dir_a / "recursive_link"
        os.symlink(dir_a, link_path)
        
        result: TraversalResult = traverser.traverse(tmp_path, config)
        
        # Expecting 'dir_a' and 'tmp_path' itself (which is the root)
        # The engine should detect 'recursive_link' is already seen and stop.
        dir_count: int = result.stats["dirs"]
        assert dir_count == 2
        
    except OSError:
        pytest.skip("Symbolic links are not supported or permitted on this host environment.")

def test_max_depth_enforcement(tmp_path: Path) -> None:
    """
    Verify that the traversal depth is strictly limited by the max_depth configuration.
    """
    current_dir: Path = tmp_path
    # Create a 5-level deep directory structure
    for i in range(5):
        current_dir = current_dir / f"level_{i}"
        current_dir.mkdir()
        
    # Limit scan to depth 2
    config: ScanConfig = ScanConfig(max_depth=2)
    traverser: DepthFirstTraverser = DepthFirstTraverser()
    result: TraversalResult = traverser.traverse(tmp_path, config)
    
    # Root is depth 0, level_0 is depth 1, level_1 is depth 2.
    assert result.stats["dirs"] == 2

def test_memory_limit_linux_mock() -> None:
    """
    Verify memory calculation logic for Linux using /proc/meminfo mock.
    """
    mock_data: List[str] = ["MemTotal:       16384000 kB"]
    
    with patch("platform.system", return_value="Linux"):
        with patch("builtins.open", MagicMock(return_value=MagicMock(__enter__=MagicMock(return_value=mock_data)))):
            mem_mb: int = get_memory_limit_mb()
            
            # 16384000 kB / 1024 = 16000 MB
            # 16000 * 0.10 (Ratio) = 1600 MB
            assert mem_mb == 1600

def test_memory_limit_macos_mock() -> None:
    """
    Verify memory calculation logic for Darwin (macOS) via sysctl mock.
    """
    # Mock 16GB in bytes
    mock_bytes: bytes = b"17179869184\n"
    
    with patch("platform.system", return_value="Darwin"):
        with patch("subprocess.check_output", return_value=mock_bytes):
            mem_mb: int = get_memory_limit_mb()
            
            # 17179869184 / 1024 / 1024 = 16384 MB
            # 16384 * 0.10 = 1638.4 -> int(1638)
            assert mem_mb == 1638

def test_memory_limit_probe_failure() -> None:
    """
    Verify that the system falls back to a safe constant if the platform is unsupported.
    """
    with patch("platform.system", return_value="UnsupportedOS"):
        mem_mb: int = get_memory_limit_mb()
        
        # Should fallback to 512MB instead of raising an exception
        assert mem_mb == _MEM_FALLBACK_MB
        assert mem_mb == 512

def test_traversal_permission_error_interception(tmp_path: Path) -> None:
    """
    Verify that PermissionError during directory iteration is caught and handled
    gracefully without crashing the entire scan.
    """
    traverser: DepthFirstTraverser = DepthFirstTraverser()
    config: ScanConfig = ScanConfig()
    
    restricted_dir: Path = tmp_path / "restricted_area"
    restricted_dir.mkdir()
    
    normal_dir: Path = tmp_path / "normal_area"
    normal_dir.mkdir()
    
    original_iterdir = Path.iterdir
    
    def mock_iterdir(self_path: Path):
        if self_path.name == "restricted_area":
            raise PermissionError("Access Denied Simulation")
        return original_iterdir(self_path)
        
    with patch.object(Path, "iterdir", new=mock_iterdir):
        result: TraversalResult = traverser.traverse(tmp_path, config)
        
    # The scan should finish successfully, counting at least the accessible directories
    assert result.stats["dirs"] >= 2