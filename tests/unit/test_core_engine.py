# Unit tests for Seedling-tools v2.5.
# Copyright (c) 2026 Kaelen Chow. All rights reserved.

from __future__ import annotations
from pathlib import Path
from typing import List, Final

from seedlingtools import ScanConfig
from seedlingtools.core.patterns import matcher_engine
from seedlingtools.core.traversal import TraversalResult, TraversalItem
from seedlingtools.utils.io_helper import io_processor

def test_text_detection() -> None:
    """
    Verify the text file identification logic via the matcher engine.
    """
    # Test valid source extensions
    assert matcher_engine.detect_text_file(Path("main.py")) is True
    
    # Test special text filenames (Makefiles, etc.)
    assert matcher_engine.detect_text_file(Path("Dockerfile")) is True
    
    # Test binary or unknown extensions
    assert matcher_engine.detect_text_file(Path("data.bin")) is False

def test_binary_probing(tmp_path: Path) -> None:
    """
    Verify the deep binary signature probing mechanism.
    """
    # Create a dummy PNG file with a valid signature
    bin_file: Path = tmp_path / "test.png"
    bin_file.write_bytes(b"\x89PNG\r\n\x1a\n\x00\x00")
    
    # Probing should identify the PNG signature as binary
    assert io_processor.probe_binary_signature(bin_file) is True
    
    # Create a standard UTF-8 text file
    txt_file: Path = tmp_path / "test.txt"
    txt_file.write_text("Normal Text Content", encoding='utf-8')
    
    # Standard text should not trigger the binary signature detection
    assert io_processor.probe_binary_signature(txt_file) is False

def test_exclusion_logic(tmp_path: Path) -> None:
    """
    Verify the path-based exclusion rule evaluation.
    """
    base: Path = tmp_path
    
    # Construct test directory structure
    build_dir: Path = base / "build"
    build_dir.mkdir()
    
    src_build_dir: Path = base / "src" / "build"
    src_build_dir.mkdir(parents=True)
    
    # Define exclusion rules (directory specific)
    rules: List[str] = ["/build/"]
    
    # Root level 'build' should be excluded
    assert matcher_engine.evaluate_exclusion_rules(build_dir, base, rules) is True
    
    # Nested 'src/build' should NOT be excluded by the root-specific rule '/build/'
    assert matcher_engine.evaluate_exclusion_rules(src_build_dir, base, rules) is False

def test_scan_target_validation(tmp_path: Path) -> None:
    """
    Verify the holistic scan target validation lifecycle.
    """
    base: Path = tmp_path
    hidden_file: Path = base / ".env"
    hidden_file.touch()
    
    # Default configuration should allow hidden files (v2.5.1 default)
    config_default: ScanConfig = ScanConfig()
    result_default: bool = matcher_engine.validate_scan_target(hidden_file, base, config_default)
    assert result_default is True
    
    # Configuration with show_hidden=False should block hidden files
    config_no_hidden: ScanConfig = ScanConfig(show_hidden=False)
    result_no_hidden: bool = matcher_engine.validate_scan_target(hidden_file, base, config_no_hidden)
    assert result_no_hidden is False

def test_traversal_result_token_estimation() -> None:
    """
    Verify the token estimation logic for LLM context optimization.
    Reference: 1 Token ≈ 4 Characters.
    """
    result: TraversalResult = TraversalResult()
    
    # Mock a traversal item
    item_path: Path = Path("/fake/script.py")
    item: TraversalItem = TraversalItem(
        path=item_path, 
        relative_path=Path("script.py"), 
        is_dir=False, 
        is_symlink=False, 
        depth=1
    )
    
    # Generate 400 characters of dummy content
    char_count: Final[int] = 400
    fake_content: str = "a" * char_count
    
    # Register content into the traversal result cache
    result.register_content_cache(item.path, fake_content, size=char_count)
    
    # Logical assertion: 400 chars // 4 = 100 estimated tokens
    expected_tokens: int = 100
    assert result.estimated_tokens == expected_tokens