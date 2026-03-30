from __future__ import annotations
import xml.etree.ElementTree as ET
from xml.dom import minidom
from pathlib import Path
from typing import List, Dict, Optional

from ..base import AbstractExporter
from ....core import ScanConfig, TraversalResult, TraversalItem
from ....utils import FileSystemError, terminal, logger

class XmlExporter(AbstractExporter):
    def export(self, target_path: Path, config: ScanConfig, result: TraversalResult, out_file: Path, is_full: bool = False) -> bool:
        if out_file.exists() is True:
            if terminal.prompt_confirmation(f"Target file '{out_file.name}' already exists. Overwrite? [y/n]: ") is False:
                logger.info("Export aborted by user.")
                return False

        root_element: ET.Element = ET.Element("ProjectAnalysis")
        
        meta_element: ET.Element = ET.SubElement(root_element, "Metadata")
        ET.SubElement(meta_element, "RootName").text = target_path.name
        ET.SubElement(meta_element, "RootPath").text = str(target_path.resolve())
        ET.SubElement(meta_element, "EstimatedTokens").text = str(result.estimated_tokens)

        stats_element: ET.Element = ET.SubElement(root_element, "Statistics")
        ET.SubElement(stats_element, "Directories").text = str(result.stats["dirs"])
        ET.SubElement(stats_element, "Files").text = str(result.stats["files"])

        tree_element: ET.Element = ET.SubElement(root_element, "DirectoryTree")
        
        items_by_parent: Dict[Path, List[TraversalItem]] = {}
        for item in result.items:
            parent: Path = item.path.parent
            if parent not in items_by_parent:
                items_by_parent[parent] = []
            items_by_parent[parent].append(item)

        self._build_xml_node(target_path, tree_element, True, target_path, items_by_parent)

        if is_full is True:
            contents_element: ET.Element = ET.SubElement(root_element, "SourceContents")
            for item in result.text_files:
                content: Optional[str] = result.get_content(item, quiet=True)
                if content is not None:
                    file_node: ET.Element = ET.SubElement(contents_element, "File")
                    file_node.set("path", str(item.relative_path))
                    file_node.text = "\n" + content + "\n"

        try:
            raw_xml_string: bytes = ET.tostring(root_element, encoding="utf-8")
            parsed_xml: minidom.Document = minidom.parseString(raw_xml_string)
            pretty_xml_string: str = parsed_xml.toprettyxml(indent="  ")

            with open(out_file, 'w', encoding='utf-8') as f:
                f.write(pretty_xml_string)
            
            logger.info(f"XML structure successfully generated ({result.estimated_tokens} tokens approximated).")
            return True
        except OSError as err:
            raise FileSystemError(
                message=f"Failed to serialize XML payload to {out_file.name}",
                context={"path": str(out_file)}
            ) from err

    def _build_xml_node(self, current_path: Path, parent_element: ET.Element, is_dir: bool, dir_path: Path, items_by_parent: Dict[Path, List[TraversalItem]]) -> None:
        rel_path_str: str = ""
        if current_path != dir_path:
            rel_path_str = str(current_path.relative_to(dir_path))
        else:
            rel_path_str = "."

        node: ET.Element = ET.SubElement(parent_element, "Item")
        node.set("name", current_path.name)
        node.set("path", rel_path_str)

        if is_dir is True:
            node.set("type", "directory")
            children_element: ET.Element = ET.SubElement(node, "Children")
            if current_path in items_by_parent:
                def _sort_key(x: TraversalItem) -> tuple[bool, str]:
                    return (x.is_dir is False, x.path.name.lower())
                    
                sorted_children: List[TraversalItem] = sorted(items_by_parent[current_path], key=_sort_key)
                for child in sorted_children:
                    self._build_xml_node(child.path, children_element, child.is_dir, dir_path, items_by_parent)
        else:
            node.set("type", "file")
            if len(current_path.suffix) > 0:
                node.set("extension", current_path.suffix.lower())
            else:
                node.set("extension", "")