from __future__ import annotations
import json
from pathlib import Path
from typing import Dict, Any, List, Optional

from ..base import AbstractExporter
from ....core import ScanConfig, TraversalResult, TraversalItem
from ....utils import logger, FileSystemError, terminal

class JsonExporter(AbstractExporter):
    def export(self, target_path: Path, config: ScanConfig, result: TraversalResult, out_file: Path, is_full: bool = False) -> bool:
        if out_file.exists() is True:
            if terminal.prompt_confirmation(f"Target file '{out_file.name}' already exists. Overwrite? [y/n]: ") is False:
                logger.info("Export aborted by user.")
                return False
                
        json_data: Dict[str, Any] = self._build_structure(target_path, result)
        
        if is_full is True:
            contents: Dict[str, str] = {}
            for item in result.text_files:
                content: Optional[str] = result.get_content(item, quiet=True)
                if content is not None:
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
            parent: Path = item.path.parent
            if parent not in items_by_parent:
                items_by_parent[parent] = []
            items_by_parent[parent].append(item)

        tree_node: Dict[str, Any] = self._build_node(dir_path, True, dir_path, items_by_parent)

        meta_dict: Dict[str, str] = {
            "root": dir_path.name, 
            "path": str(dir_path.resolve())
        }
        
        stats_dict: Dict[str, int] = {
            "directories": result.stats["dirs"], 
            "files": result.stats["files"]
        }
        
        final_struct: Dict[str, Any] = {
            "meta": meta_dict,
            "stats": stats_dict,
            "tree": tree_node
        }
        
        return final_struct

    def _build_node(self, current_path: Path, is_dir: bool, dir_path: Path, items_by_parent: Dict[Path, List[TraversalItem]]) -> Dict[str, Any]:
        rel_path: str = ""
        if current_path != dir_path:
            rel_path = str(current_path.relative_to(dir_path))
        else:
            rel_path = "."
            
        node_type: str = ""
        if is_dir is True:
            node_type = "directory"
        else:
            node_type = "file"
            
        node: Dict[str, Any] = {
            "name": current_path.name,
            "type": node_type,
            "path": rel_path
        }
        
        if is_dir is False:
            ext: Optional[str] = None
            if len(current_path.suffix) > 0:
                ext = current_path.suffix.lower()
            node["extension"] = ext
        else:
            children: List[Dict[str, Any]] = []
            if current_path in items_by_parent:
                def _sort_key(x: TraversalItem) -> tuple[bool, str]:
                    return (x.is_dir is False, x.path.name.lower())
                    
                sorted_children: List[TraversalItem] = sorted(items_by_parent[current_path], key=_sort_key)
                for child in sorted_children:
                    child_node: Dict[str, Any] = self._build_node(child.path, child.is_dir, dir_path, items_by_parent)
                    children.append(child_node)
            node["children"] = children
            
        return node