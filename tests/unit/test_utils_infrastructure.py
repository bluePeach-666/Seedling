# Unit tests for Seedling-tools v2.5.
# Copyright (c) 2026 Kaelen Chow. All rights reserved.

from __future__ import annotations
from pathlib import Path
from typing import Dict, Final

from seedlingtools.utils.io_helper import io_processor

def test_markdown_fence_calculation() -> None:
    """
    Verify the dynamic calculation of Markdown code block fences to prevent collisions.
    """
    # Simple content should use standard triple backticks
    case_1: str = "simple code line"
    assert io_processor.calculate_markdown_fence(case_1) == "```"
    
    # Content containing backticks should escalate the fence length
    case_2: str = "```\nnested block\n```"
    assert io_processor.calculate_markdown_fence(case_2) == "````"

def test_path_security_boundary(tmp_path: Path) -> None:
    """
    Verify the path traversal protection mechanism.
    """
    safe_dir: Path = tmp_path / "safe_zone"
    safe_dir.mkdir()
    
    internal_file: Path = safe_dir / "authorized.txt"
    external_file: Path = tmp_path / "malicious_traversal.txt"
    
    # File inside the root should be validated as safe
    is_internal_safe: bool = io_processor.validate_path_security(internal_file, safe_dir)
    assert is_internal_safe is True
    
    # File outside the designated root should be blocked
    is_external_safe: bool = io_processor.validate_path_security(external_file, safe_dir)
    assert is_external_safe is False

def test_blueprint_deserialization(tmp_path: Path) -> None:
    """
    Verify the parsing logic for structured Markdown blueprint files.
    """
    blueprint_path: Path = tmp_path / "blueprint_spec.md"
    
    # Construct a valid fenced block blueprint
    mock_content: Final[str] = """
### FILE: src/kernel.py
```python
import sys
print('Engine Core Loaded')
```
"""
    blueprint_path.write_text(mock_content, encoding='utf-8')

    # Execute deserialization via the global IO processor
    contents_map: Dict[str, str] = io_processor.deserialize_fenced_blocks(blueprint_path)
    
    # Assert mapping accuracy
    assert "src/kernel.py" in contents_map
    
    extracted_source: str = contents_map["src/kernel.py"]
    assert "Engine Core Loaded" in extracted_source
    assert "import sys" in extracted_source
