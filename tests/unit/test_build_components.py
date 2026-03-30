# Unit tests for Seedling-tools v2.5.
# Copyright (c) 2026 Kaelen Chow. All rights reserved.

from __future__ import annotations
from pathlib import Path
from typing import List, Dict, Any, Tuple
from unittest.mock import MagicMock, patch

from seedlingtools.commands.build.parsers.text_parser import TextBlueprintParser
from seedlingtools.commands.build.executors.local_fs import LocalFSExecutor
from seedlingtools.utils import io_processor

def test_text_blueprint_parser_mapping(tmp_path: Path) -> None:
    parser: TextBlueprintParser = TextBlueprintParser()
    target_path: Path = (tmp_path / "target").resolve()
    if target_path.exists() is False:
        target_path.mkdir(parents=True)

    parsed_items: List[Dict[str, Any]] = [
        {
            'name': 'main.py',
            'depth': 1,
            'is_dir': False,
            'safe_path': (target_path / "src" / "main.py").resolve()
        }
    ]
    
    file_contents: Dict[str, str] = {
        "src/main.py": "print('hello')"
    }
    
    safe_contents: Dict[str, Tuple[Path, str]] = parser._align_and_verify_contents(
        contents=file_contents,
        target_path=target_path,
        root_name="test_project",
        parsed_items=parsed_items
    )
    
    assert "src/main.py" in safe_contents
    actual_path: Path = safe_contents["src/main.py"][0]
    assert actual_path.is_absolute() is True
    assert str(actual_path).startswith(str(target_path)) is True


def test_local_fs_executor_force_mode(tmp_path: Path) -> None:
    executor: LocalFSExecutor = LocalFSExecutor()
    target_path: Path = tmp_path
    
    conflict_file: Path = target_path / "conflict.txt"
    conflict_file.write_text("OLD CONTENT", encoding="utf-8")
    
    parsed_items: List[Dict[str, Any]] = [
        {
            'depth': 0, 
            'name': 'conflict.txt', 
            'is_dir': False, 
            'safe_path': conflict_file
        }
    ]
    contents: Dict[str, Tuple[Path, str]] = {
        "conflict.txt": (conflict_file, "NEW CONTENT")
    }
    
    success: bool = executor.execute(
        parsed_items=parsed_items, 
        contents=contents, 
        target_path=target_path, 
        force_mode=True
    )
    
    assert success is True
    assert conflict_file.read_text(encoding="utf-8") == "NEW CONTENT"


@patch("seedlingtools.commands.build.executors.local_fs.terminal.prompt_confirmation")
def test_local_fs_executor_normal_mode_declined(mock_prompt: MagicMock, tmp_path: Path) -> None:
    executor: LocalFSExecutor = LocalFSExecutor()
    target_path: Path = tmp_path
    
    conflict_file: Path = target_path / "safe.txt"
    conflict_file.write_text("SAFE CONTENT", encoding="utf-8")
    
    parsed_items: List[Dict[str, Any]] = [
        {'depth': 0, 'name': 'safe.txt', 'is_dir': False, 'safe_path': conflict_file}
    ]
    contents: Dict[str, Tuple[Path, str]] = {
        "safe.txt": (conflict_file, "DANGEROUS CONTENT")
    }
    
    mock_prompt.return_value = False
    
    success: bool = executor.execute(
        parsed_items=parsed_items, 
        contents=contents, 
        target_path=target_path, 
        force_mode=False
    )
    
    assert success is True
    assert conflict_file.read_text(encoding="utf-8") == "SAFE CONTENT"