from __future__ import annotations
import pytest # type: ignore
from pathlib import Path
from typing import List, Dict, Any
from unittest.mock import MagicMock, patch

from seedlingtools.core import ScanConfig, TraversalResult, TraversalItem
from seedlingtools.commands.scan.plugins.analyzer import AnalyzerPlugin, ProjectAnalysis
from seedlingtools.commands.scan.plugins.grep import GrepPlugin, GrepMatch
from seedlingtools.commands.scan.plugins.search import SearchPlugin

def _create_mock_item(name: str, is_dir: bool, depth: int) -> TraversalItem:
    base_path: Path = Path("/fake/root")
    target_path: Path = base_path / name
    return TraversalItem(
        path=target_path,
        relative_path=Path(name),
        is_dir=is_dir,
        is_symlink=False,
        depth=depth
    )

def test_analyzer_plugin_detects_nodejs_dependencies() -> None:
    plugin: AnalyzerPlugin = AnalyzerPlugin()
    result: TraversalResult = TraversalResult()
    
    pkg_item: TraversalItem = _create_mock_item("package.json", is_dir=False, depth=1)
    result.items.append(pkg_item)
    result.text_files.append(pkg_item)
    
    mock_json: str = '{"dependencies": {"react": "^18.0.0"}, "devDependencies": {"jest": "^29.0.0"}}'
    result._content_cache[pkg_item.path] = mock_json
    
    analysis: ProjectAnalysis = plugin._analyze(result)
    
    assert analysis.project_type == "node"
    assert "react" in analysis.dependencies.get("direct", [])
    assert "jest" in analysis.dependencies.get("dev", [])

def test_grep_plugin_context_extraction() -> None:
    plugin: GrepPlugin = GrepPlugin(pattern="TARGET", context_lines=1)
    result: TraversalResult = TraversalResult()
    config: ScanConfig = ScanConfig(use_regex=False, ignore_case=False)
    
    file_item: TraversalItem = _create_mock_item("test.txt", is_dir=False, depth=1)
    result.text_files.append(file_item)
    
    mock_content: str = "Line 1\nLine 2\nThis is the TARGET line\nLine 4\nLine 5"
    result._content_cache[file_item.path] = mock_content
    
    matches: List[GrepMatch] = plugin._search_contents(result, config)
    
    assert len(matches) == 1
    match: GrepMatch = matches[0]
    
    assert match.line_number == 3
    assert match.line_content == "This is the TARGET line"
    
    assert len(match.context_before) == 1
    assert match.context_before[0] == "Line 2"
    
    assert len(match.context_after) == 1
    assert match.context_after[0] == "Line 4"

@patch("seedlingtools.commands.scan.plugins.search.StandardTreeRenderer")
def test_search_plugin_invokes_renderer(mock_renderer_class: MagicMock, tmp_path: Path) -> None:
    plugin: SearchPlugin = SearchPlugin(keyword="findme", delete_mode=False, dry_run=False)
    result: TraversalResult = TraversalResult()
    config: ScanConfig = ScanConfig()
    
    match_item: TraversalItem = _create_mock_item("findme.txt", is_dir=False, depth=1)
    result.items.append(match_item)
    
    mock_renderer_instance = mock_renderer_class.return_value
    mock_renderer_instance.render.return_value = ["└── findme.txt [MATCHED]"]
    
    out_file: Path = tmp_path / "search_report.md"
    
    plugin._generate_contextual_report(
        all_matches=[match_item.path],
        exact=[match_item.path],
        fuzzy=[],
        target_path=Path("/fake/root"),
        config=config,
        result=result,
        out_file=out_file,
        format_type='md'
    )
    
    assert match_item.path in config.highlights
    
    mock_renderer_instance.render.assert_called_once_with(
        result, 
        config, 
        root_path=Path("/fake/root")
    )
    
    assert out_file.exists()