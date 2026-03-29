from __future__ import annotations
import pytest # type: ignore
from pathlib import Path
from typing import List, Dict, Any, Tuple
from unittest.mock import MagicMock, patch

from seedlingtools.commands.build.parsers.text_parser import TextBlueprintParser
from seedlingtools.commands.build.executors.local_fs import LocalFSExecutor
from seedlingtools.utils import io_processor

def test_text_blueprint_parser_mapping() -> None:
    parser: TextBlueprintParser = TextBlueprintParser()
    target_path: Path = Path("/safe/target")
    
    raw_items: List[Dict[str, Any]] = [
        {'depth': 0, 'name': 'root', 'is_dir': True},
        {'depth': 1, 'name': 'src', 'is_dir': True},
        {'depth': 2, 'name': 'main.py', 'is_dir': False}
    ]
    
    file_contents: Dict[str, str] = {
        "src/main.py": "print('hello')"
    }
    
    with patch.object(io_processor, 'validate_path_security', return_value=True):
        parsed_items: List[Dict[str, Any]] = parser._parse_to_safe_paths(raw_items, target_path)
        
        assert len(parsed_items) == 2
        
        dir_node: Dict[str, Any] = parsed_items[0]
        assert dir_node['name'] == 'src'
        assert dir_node['is_dir'] is True
        
        safe_contents: Dict[str, Tuple[Path, str]] = parser._align_and_verify_contents(
            contents=file_contents,
            target_path=target_path,
            root_name="root",
            parsed_items=parsed_items
        )
        
        assert "src/main.py" in safe_contents
        mapped_path, mapped_content = safe_contents["src/main.py"]
        assert mapped_content == "print('hello')"


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