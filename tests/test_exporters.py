from __future__ import annotations
import pytest # type: ignore
import json
from pathlib import Path
from typing import Dict, Any

from seedlingtools.core import ScanConfig, TraversalResult, TraversalItem
from seedlingtools.commands.scan.exporters.json_output import JsonExporter
from seedlingtools.commands.scan.exporters.text_output import TextExporter

def _create_fake_result() -> TraversalResult:
    result: TraversalResult = TraversalResult()
    
    root_dir: TraversalItem = TraversalItem(
        path=Path("/test_root"), relative_path=Path("."), is_dir=True, is_symlink=False, depth=0
    )
    file_item: TraversalItem = TraversalItem(
        path=Path("/test_root/script.py"), relative_path=Path("script.py"), is_dir=False, is_symlink=False, depth=1
    )
    
    result.items = [root_dir, file_item]
    result.directories = [root_dir]
    result.text_files = [file_item]
    result.stats = {"dirs": 1, "files": 1}
    
    result._content_cache[file_item.path] = "print('exported')"
    return result

def test_json_exporter_format(tmp_path: Path) -> None:
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
    assert out_file.exists()
    
    with open(out_file, 'r', encoding='utf-8') as f:
        data: Dict[str, Any] = json.load(f)
        
    assert "meta" in data
    assert data["meta"]["root"] == "test_root"
    
    assert "stats" in data
    assert data["stats"]["files"] == 1
    
    assert "contents" in data
    assert "script.py" in data["contents"]
    assert data["contents"]["script.py"] == "print('exported')"

def test_text_exporter_markdown_fences(tmp_path: Path) -> None:
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
    
    assert "# Directory Structure Stats: `/test_root`" in content
    
    assert "FULL PROJECT CONTENT" in content
    
    assert "### FILE: script.py" in content
    assert "```py\nprint('exported')\n```" in content