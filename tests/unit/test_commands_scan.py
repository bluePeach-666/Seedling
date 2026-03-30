# Unit tests for Seedling-tools v2.5.
# Copyright (c) 2026 Kaelen Chow. All rights reserved.

from __future__ import annotations
import pytest #type: ignore
from unittest.mock import patch
from pathlib import Path
from typing import List

from seedlingtools import (
    ScanConfig, 
    TraversalResult
)
from seedlingtools.commands.scan.explorer import ScanOrchestrator
from seedlingtools.commands.scan.plugins.grep import GrepPlugin, GrepMatch
from seedlingtools.commands.scan.plugins.analyzer import AnalyzerPlugin, ProjectAnalysis
from seedlingtools.commands.scan.exporters.json_output import JsonExporter
from seedlingtools.core.traversal import DepthFirstTraverser
from seedlingtools.commands.scan.helper import intercept_garbage_files

@pytest.fixture
def sample_project(tmp_path: Path) -> Path:
    """
    Construct a deterministic project structure for testing.
    """
    src: Path = tmp_path / "src"
    src.mkdir()
    
    main_py: Path = src / "main.py"
    main_py.write_text("DEBUG = True\n", encoding='utf-8')
    
    pkg_json: Path = tmp_path / "package.json"
    pkg_json.write_text('{"dependencies": {"express": "4.17.1"}}', encoding='utf-8')
    
    node_modules: Path = tmp_path / "node_modules"
    node_modules.mkdir()
    
    return tmp_path

def test_grep_plugin_logic(sample_project: Path) -> None:
    config: ScanConfig = ScanConfig()
    traverser: DepthFirstTraverser = DepthFirstTraverser()
    
    # 显式采集内容
    result: TraversalResult = traverser.traverse(sample_project, config, collect_content=True)
    
    plugin: GrepPlugin = GrepPlugin(pattern="DEBUG", context_lines=1)
    # 调用内部搜索方法进行逻辑验证
    matches: List[GrepMatch] = plugin._search_contents(result, config)
    
    assert len(matches) == 1
    assert matches[0].line_content == "DEBUG = True"
    assert matches[0].line_number == 1

def test_analyzer_plugin(sample_project: Path) -> None:
    config: ScanConfig = ScanConfig()
    traverser: DepthFirstTraverser = DepthFirstTraverser()
    result: TraversalResult = traverser.traverse(sample_project, config)
    
    plugin: AnalyzerPlugin = AnalyzerPlugin()
    analysis: ProjectAnalysis = plugin._analyze(sample_project, result)
    
    # 严格校验项目类型判定逻辑
    assert analysis.project_type == "node"
    
    # 严格校验依赖提取逻辑
    assert "direct" in analysis.dependencies
    direct_deps: List[str] = analysis.dependencies["direct"]
    assert "express" in direct_deps

def test_orchestrator_pipeline(tmp_path: Path, sample_project: Path) -> None:
    config: ScanConfig = ScanConfig()
    traverser: DepthFirstTraverser = DepthFirstTraverser()
    result: TraversalResult = traverser.traverse(sample_project, config)
    
    out_file: Path = tmp_path / "output.json"
    exporter: JsonExporter = JsonExporter()
    orchestrator: ScanOrchestrator = ScanOrchestrator(exporter=exporter)
    
    # 执行物理构建管线
    orchestrator.run_pipeline(sample_project, config, result, out_file=out_file)
    
    assert out_file.exists() is True
    assert out_file.is_file() is True

def test_garbage_interception_non_interactive(sample_project: Path) -> None:
    """
    Verify that in non-interactive mode, garbage files do not alter excludes.
    """
    with patch("sys.stdin.isatty", return_value=False):
        with patch("sys.stdout.isatty", return_value=False):
            excludes: List[str] = intercept_garbage_files(
                target_path=sample_project,
                current_excludes=[],
                is_no_hidden=False,
                is_explicit_ignore=False
            )
            # 在非交互模式下，由于无法确认，应保持原样
            assert len(excludes) == 0

def test_garbage_interception_explicit_intent(sample_project: Path) -> None:
    """
    Verify that explicit ignore intent blocks interactive prompts.
    """
    initial_excludes: List[str] = ["custom_ignore"]
    excludes: List[str] = intercept_garbage_files(
        target_path=sample_project,
        current_excludes=initial_excludes,
        is_no_hidden=False,
        is_explicit_ignore=True  # 显式设定了忽略意图
    )
    
    assert len(excludes) == 1
    assert excludes[0] == "custom_ignore"