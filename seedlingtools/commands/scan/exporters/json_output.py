from __future__ import annotations
import json
from pathlib import Path
from typing import Dict, Any, List
from ..base import AbstractExporter
from ....core import ScanConfig, TraversalResult, TraversalItem
from ....utils import logger, FileSystemError, terminal

class JsonExporter(AbstractExporter):
    """JSON 格式化导出适配器"""

    def export(self, target_path: Path, config: ScanConfig, result: TraversalResult, out_file: Path, is_full: bool = False) -> bool:
        if out_file.exists():
            if not terminal.prompt_confirmation(f"Target file '{out_file.name}' already exists. Overwrite? [y/n]: "):
                logger.info("Export aborted by user.")
                return False
            
        json_data: Dict[str, Any] = self._build_structure(target_path, result)
        
        if is_full:
            contents: Dict[str, str] = {}
            for item in result.text_files:
                content: str | None = result.get_content(item, quiet=True)
                if content:
                    contents[str(item.relative_path)] = content
            json_data["contents"] = contents

        try:
            with open(out_file, 'w', encoding='utf-8') as f:
                json.dump(json_data, f, indent=2, ensure_ascii=False)
            return True
        except OSError as err:
            raise FileSystemError(
                message=f"Failed to serialize JSON payload to {out_file.name}",
                context={"path": str(out_file)}
            ) from err

    def _build_structure(self, dir_path: Path, result: TraversalResult) -> Dict[str, Any]:
        items_by_parent: Dict[Path, List[TraversalItem]] = {}
        for item in result.items:
            items_by_parent.setdefault(item.path.parent, []).append(item)

        def _build_node(current_path: Path, is_dir: bool) -> Dict[str, Any]:
            rel_path: str = str(current_path.relative_to(dir_path)) if current_path != dir_path else "."
            node: Dict[str, Any] = {
                "name": current_path.name,
                "type": "directory" if is_dir else "file",
                "path": rel_path
            }
            
            if not is_dir:
                node["extension"] = current_path.suffix.lower() if current_path.suffix else None
            else:
                children: List[Dict[str, Any]] = []
                if current_path in items_by_parent:
                    sorted_children = sorted(items_by_parent[current_path], key=lambda x: (not x.is_dir, x.path.name.lower()))
                    for child in sorted_children:
                        children.append(_build_node(child.path, child.is_dir))
                node["children"] = children
            return node

        return {
            "meta": {"root": dir_path.name, "path": str(dir_path.resolve())},
            "stats": {"directories": result.stats["dirs"], "files": result.stats["files"]},
            "tree": _build_node(dir_path, True)
        }