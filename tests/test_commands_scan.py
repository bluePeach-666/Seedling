import pytest #type: ignore
from pathlib import Path
from seedlingtools import (
    ScanConfig, 
    ScanOrchestrator, 
    GrepPlugin, 
    AnalyzerPlugin, 
    JsonExporter
)
from seedlingtools.core import DepthFirstTraverser 

@pytest.fixture
def sample_project(tmp_path):
    src = tmp_path / "src"
    src.mkdir()
    (src / "main.py").write_text("DEBUG = True\n", encoding='utf-8')
    (tmp_path / "package.json").write_text('{"dependencies": {"express": "4.17.1"}}', encoding='utf-8')
    return tmp_path

def test_grep_plugin_logic(sample_project):
    config = ScanConfig()
    traverser = DepthFirstTraverser()
    result = traverser.traverse(sample_project, config, collect_content=True)
    
    plugin = GrepPlugin(pattern="DEBUG", context_lines=1)
    matches = plugin._search_contents(result, config)
    
    assert len(matches) == 1
    assert matches[0].line_content == "DEBUG = True"

def test_analyzer_plugin(sample_project):
    config = ScanConfig()
    result = DepthFirstTraverser().traverse(sample_project, config)
    
    plugin = AnalyzerPlugin()
    analysis = plugin._analyze(result)
    
    assert "node" in analysis.project_type
    assert "express" in analysis.dependencies["direct"]

def test_orchestrator_pipeline(tmp_path, sample_project):
    config = ScanConfig()
    result = DepthFirstTraverser().traverse(sample_project, config)
    
    out_file = tmp_path / "output.json"
    orchestrator = ScanOrchestrator(exporter=JsonExporter())
    
    orchestrator.run_pipeline(sample_project, config, result, out_file=out_file)
    assert out_file.exists()