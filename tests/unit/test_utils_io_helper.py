# Unit tests for Seedling-tools v2.5.
# Copyright (c) 2026 Kaelen Chow. All rights reserved.

from pathlib import Path
from typing import List, Dict, Any

from seedlingtools.utils import io_processor

def test_parse_tree_topology_extract_raw_items() -> None:
    tree_lines: List[str] = [
        "root/",
        "    nested_folder/",
        "        file.py"
    ]
    
    raw_items: List[Dict[str, Any]] = io_processor.parse_tree_topology(tree_lines)
    
    folder_node: Dict[str, Any] = {}
    for item in raw_items:
        if item['name'] == "nested_folder":
            folder_node = item
            break
            
    assert folder_node['is_dir'] is True
    assert folder_node['depth'] == 1


def test_parse_tree_topology_implicit_directory_inference() -> None:
    tree_lines: List[str] = [
        "root/",
        "    implicit_folder",
        "        file.py"
    ]
    
    raw_items: List[Dict[str, Any]] = io_processor.parse_tree_topology(tree_lines)
    
    folder_node: Dict[str, Any] = {}
    for item in raw_items:
        if item['name'] == "implicit_folder":
            folder_node = item
            break
            
    assert folder_node['is_dir'] is True 


def test_io_processor_compare_file_content(tmp_path: Path) -> None:
    file_path: Path = tmp_path / "test.txt"
    
    file_path.write_text("Original", encoding='utf-8')
    
    is_mismatched_original: bool = io_processor.compare_file_content(path=file_path, expected_content="Original")
    is_mismatched_modified: bool = io_processor.compare_file_content(path=file_path, expected_content="Modified")
    
    assert is_mismatched_original is False
    assert is_mismatched_modified is True