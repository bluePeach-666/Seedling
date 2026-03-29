from __future__ import annotations
from pathlib import Path
from typing import List
from ..base import AbstractExporter
from ....core import ScanConfig, TraversalResult, StandardTreeRenderer
from ....utils import image_renderer, io_processor, FileSystemError, terminal, logger

class TextExporter(AbstractExporter):
    """纯文本、Markdown 与图像渲染导出适配器"""

    def __init__(self, format_type: str = 'md'):
        self.format_type: str = format_type
        self.tree_renderer = StandardTreeRenderer()

    def export(self, target_path: Path, config: ScanConfig, result: TraversalResult, out_file: Path, is_full: bool = False) -> bool:
        lines: List[str] = self.tree_renderer.render(result, config, root_path=target_path)
        root_name: str = target_path.name or str(target_path)
        tree_text: str = f"{root_name}/\n" + "\n".join(lines) + f"\n\n[ {result.stats['dirs']} directories, {result.stats['files']} files ]"

        if out_file.exists():
            if not terminal.prompt_confirmation(f"Target file '{out_file.name}' already exists. Overwrite? [y/n]: "):
                logger.info("Export aborted by user.")
                return False
            
        full_content: str = ""
        if is_full:
            full_content = self._aggregate_full_content(result, config)
            if self.format_type == 'image':
                self.format_type = 'md'
                out_file = out_file.with_suffix('.md')
            
        try:
            if self.format_type == 'md':
                with open(out_file, 'w', encoding='utf-8') as f:
                    f.write(f"# Directory Structure Stats: `{target_path}`\n\n```text\n{tree_text}\n```\n")
                    f.write(full_content)
                return True
            elif self.format_type == 'txt':
                with open(out_file, 'w', encoding='utf-8') as f:
                    f.write(tree_text + "\n" + full_content)
                return True
            elif self.format_type == 'image':
                return image_renderer.render_text_to_image(tree_text, out_file, len(lines))
        except OSError as err:
            raise FileSystemError(
                message=f"Failed to write exported data to {out_file.name}",
                context={"path": str(out_file)}
            ) from err
            
        return False

    def _aggregate_full_content(self, result: TraversalResult, config: ScanConfig) -> str:
        sections: List[str] = ["\n\n" + "="*60, "FULL PROJECT CONTENT", "="*60 + "\n"]
        for item in result.text_files:
            content: str | None = result.get_content(item, quiet=config.quiet)
            if content:
                fence: str = io_processor.calculate_markdown_fence(content)
                lang: str = item.path.suffix.lstrip('.')
                sections.append(f"### FILE: {item.relative_path}\n{fence}{lang}\n{content}\n{fence}\n")
        return "\n".join(sections)