# Unit tests for Seedling-tools v2.5.
# Copyright (c) 2026 Kaelen Chow. All rights reserved.

from pathlib import Path
from typing import List, Dict, Any, Tuple
from unittest.mock import MagicMock

from seedlingtools.commands.build.architect import BuildOrchestrator
from seedlingtools.commands.build.base import AbstractBlueprintParser, AbstractBuildExecutor

def test_build_orchestrator_pipeline_success() -> None:
    mock_parser: MagicMock = MagicMock(spec=AbstractBlueprintParser)
    mock_executor: MagicMock = MagicMock(spec=AbstractBuildExecutor)
    
    dummy_parsed_items: List[Dict[str, Any]] = [{'name': 'src', 'depth': 0, 'is_dir': True, 'safe_path': Path('/fake/src')}]
    dummy_contents: Dict[str, Tuple[Path, str]] = {'src/main.py': (Path('/fake/src/main.py'), 'print("hello")')}
    
    mock_parser.parse.return_value = (dummy_parsed_items, dummy_contents)
    mock_executor.execute.return_value = True

    orchestrator: BuildOrchestrator = BuildOrchestrator(parser=mock_parser, executor=mock_executor)
    
    source_file: Path = Path("/fake/blueprint.md")
    target_dir: Path = Path("/fake/target")
    
    result: bool = orchestrator.run_pipeline(source_file=source_file, target_dir=target_dir, force_mode=False)
    
    assert result is True
    
    mock_parser.parse.assert_called_once_with(source_file, target_dir.resolve(strict=False))
    
    mock_executor.execute.assert_called_once_with(
        parsed_items=dummy_parsed_items, 
        contents=dummy_contents, 
        target_path=target_dir.resolve(strict=False), 
        force_mode=False
    )

def test_build_orchestrator_pipeline_abort_on_empty_parse() -> None:
    mock_parser: MagicMock = MagicMock(spec=AbstractBlueprintParser)
    mock_executor: MagicMock = MagicMock(spec=AbstractBuildExecutor)
    
    empty_parsed_items: List[Dict[str, Any]] = []
    empty_contents: Dict[str, Tuple[Path, str]] = {}
    mock_parser.parse.return_value = (empty_parsed_items, empty_contents)

    orchestrator: BuildOrchestrator = BuildOrchestrator(parser=mock_parser, executor=mock_executor)
    
    source_file: Path = Path("/fake/empty_blueprint.md")
    target_dir: Path = Path("/fake/target")
    
    result: bool = orchestrator.run_pipeline(source_file=source_file, target_dir=target_dir, force_mode=False)
    
    assert result is False
    
    mock_executor.execute.assert_not_called()