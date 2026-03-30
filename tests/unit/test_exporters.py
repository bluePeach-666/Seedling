# Unit tests for Seedling-tools v2.5.
# Copyright (c) 2026 Kaelen Chow. All rights reserved.

from __future__ import annotations
import json
from pathlib import Path
from typing import Dict, Any, Final

from seedlingtools.core.config import ScanConfig
from seedlingtools.core.traversal import TraversalResult, TraversalItem
from seedlingtools.commands.scan.exporters.json_output import JsonExporter
from seedlingtools.commands.scan.exporters.text_output import TextExporter
from seedlingtools.commands.scan.exporters.xml_output import XmlExporter

def _create_fake_result() -> TraversalResult:
    """
    Construct a deterministic TraversalResult object for testing exporters.
    """
    result: TraversalResult = TraversalResult()
    
    root_path: Path = Path("/test_root")
    script_path: Path = root_path / "script.py"
    
    root_dir: TraversalItem = TraversalItem(
        path=root_path, 
        relative_path=Path("."), 
        is_dir=True, 
        is_symlink=False, 
        depth=0
    )
    
    file_item: TraversalItem = TraversalItem(
        path=script_path, 
        relative_path=Path("script.py"), 
        is_dir=False, 
        is_symlink=False, 
        depth=1
    )
    
    result.items = [root_dir, file_item]
    result.directories = [root_dir]
    result.text_files = [file_item]
    
    result.stats["dirs"] = 1
    result.stats["files"] = 1
    
    # Mock content cache for full export tests
    source_code: Final[str] = "print('exported')"
    result.register_content_cache(file_item.path, source_code, size=len(source_code))
    
    return result

def test_json_exporter_format(tmp_path: Path) -> None:
    """
    Verify JSON exporter produces valid schema and correct metadata.
    """
    exporter: JsonExporter = JsonExporter()
    config: ScanConfig = ScanConfig()
    result: TraversalResult = _create_fake_result()
    out_file: Path = tmp_path / "out.json"
    
    success: bool = exporter.export(
        target_path=Path("/test_root"), 
        config=config, 
        result=result, 
        out_file=out_file, 
        is_full=True
    )
    
    assert success is True
    
    # Validate content
    raw_json: str = out_file.read_text(encoding='utf-8')
    data: Dict[str, Any] = json.loads(raw_json)
        
    assert "meta" in data
    assert data["meta"]["root"] == "test_root"
    assert data["stats"]["files"] == 1
    assert "contents" in data
    assert data["contents"]["script.py"] == "print('exported')"

def test_text_exporter_markdown_fences(tmp_path: Path) -> None:
    """
    Verify Markdown exporter creates structured reports with source injection.
    """
    exporter: TextExporter = TextExporter(format_type='md')
    config: ScanConfig = ScanConfig()
    result: TraversalResult = _create_fake_result()
    out_file: Path = tmp_path / "out.md"
    
    success: bool = exporter.export(
        target_path=Path("/test_root"), 
        config=config, 
        result=result, 
        out_file=out_file, 
        is_full=True
    )
    
    assert success is True
    content: str = out_file.read_text(encoding='utf-8')
    
    # Assert headers and token metadata
    assert "# Directory Structure Stats" in content
    assert "Approx." in content
    assert "tokens" in content
    
    # Assert full content section
    assert "FULL PROJECT CONTENT" in content
    assert "### FILE: script.py" in content
    
    # Refined assertion for expanded industrial formatting (multiple newlines)
    assert "```py" in content
    assert "print('exported')" in content
    assert "```" in content

def test_xml_exporter_format(tmp_path: Path) -> None:
    """
    Verify XML exporter handles nesting and attributes correctly.
    """
    exporter: XmlExporter = XmlExporter()
    config: ScanConfig = ScanConfig()
    result: TraversalResult = _create_fake_result()
    out_file: Path = tmp_path / "out.xml"
    
    success: bool = exporter.export(
        target_path=Path("/test_root"), 
        config=config, 
        result=result, 
        out_file=out_file, 
        is_full=True
    )
    
    assert success is True
    content: str = out_file.read_text(encoding='utf-8')
    
    # Structural XML assertions
    assert "<ProjectAnalysis>" in content
    assert "<EstimatedTokens>" in content
    assert "<DirectoryTree>" in content
    assert "<SourceContents>" in content
    
    # Content assertions
    assert 'path="script.py"' in content
    assert "print('exported')" in content