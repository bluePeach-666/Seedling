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


def test_parse_tree_topology_ignores_visual_connector_noise() -> None:
    tree_lines: List[str] = [
        "root/",
        "├── src/",
        "│",
        "│   │",
        "│   ├── app.py",
        "└── README.md"
    ]

    raw_items: List[Dict[str, Any]] = io_processor.parse_tree_topology(tree_lines)

    names: List[str] = []
    for item in raw_items:
        names.append(item['name'])

    assert names == ["root", "src", "app.py", "README.md"]


def test_parse_tree_topology_preserves_valid_glyph_names() -> None:
    tree_lines: List[str] = [
        "root/",
        "├── notes│2026.md",
        "├── glyph─name.txt",
        "├── branch├marker.py",
        "├── │literal-pipe.txt",
        "├── └literal-corner.txt",
        "└── ├──test.py"
    ]

    raw_items: List[Dict[str, Any]] = io_processor.parse_tree_topology(tree_lines)

    names: List[str] = []
    for item in raw_items:
        names.append(item['name'])

    assert "notes│2026.md" in names
    assert "glyph─name.txt" in names
    assert "branch├marker.py" in names
    assert "│literal-pipe.txt" in names
    assert "└literal-corner.txt" in names
    assert "├──test.py" in names


def test_parse_tree_topology_rejects_malformed_visual_prefixes() -> None:
    tree_lines: List[str] = [
        "root/",
        "│ ├── bad.txt",
        "└─ also_bad.txt",
        "─ bad_again.txt",
        "└── good.txt"
    ]

    raw_items: List[Dict[str, Any]] = io_processor.parse_tree_topology(tree_lines)

    names: List[str] = []
    for item in raw_items:
        names.append(item['name'])

    assert names == ["root", "good.txt"]


def test_io_processor_compare_file_content(tmp_path: Path) -> None:
    file_path: Path = tmp_path / "test.txt"
    
    file_path.write_text("Original", encoding='utf-8')
    
    is_mismatched_original: bool = io_processor.compare_file_content(path=file_path, expected_content="Original")
    is_mismatched_modified: bool = io_processor.compare_file_content(path=file_path, expected_content="Modified")
    
    assert is_mismatched_original is False
    assert is_mismatched_modified is True