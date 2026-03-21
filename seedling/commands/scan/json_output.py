"""JSON output module for programmatic consumption."""
import json
from pathlib import Path
from typing import Dict, Any, List, Optional
from seedling.core.filesystem import ScanConfig, is_valid_item


def build_json_structure(dir_path: Path, config: ScanConfig, stats: Dict[str, int]) -> Dict[str, Any]:
    """Build nested JSON structure representing the directory tree."""
    result = {
        "meta": {
            "root": dir_path.name,
            "path": str(dir_path.resolve()),
        },
        "stats": {
            "directories": stats.get("dirs", 0),
            "files": stats.get("files", 0)
        },
        "tree": _build_node(dir_path, dir_path, config)
    }
    return result


def _build_node(current: Path, base: Path, config: ScanConfig) -> Dict[str, Any]:
    """Recursively build JSON node for a path."""
    node = {
        "name": current.name,
        "type": "directory" if current.is_dir() else "file",
        "path": str(current.relative_to(base))
    }

    if current.is_file():
        node["extension"] = current.suffix.lower() or None # type: ignore
    elif current.is_dir():
        children = []
        try:
            items = sorted(current.iterdir(), key=lambda x: (not x.is_dir(), x.name.lower()))
            for item in items:
                if is_valid_item(item, base, config):
                    children.append(_build_node(item, base, config))
        except PermissionError:
            node["error"] = "Permission Denied"
        node["children"] = children # type: ignore

    return node


def write_json(data: Dict[str, Any], output_file: Path) -> bool:
    """Write JSON data to file."""
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        from seedling.core.logger import logger
        logger.error(f"Failed to write JSON: {e}")
        return False


def build_json_with_contents(dir_path: Path, config: ScanConfig, stats: Dict[str, int],
                              contents: Dict[str, str]) -> Dict[str, Any]:
    """Build JSON structure with file contents included."""
    result = build_json_structure(dir_path, config, stats)
    result["contents"] = contents
    return result
