from __future__ import annotations
from pathlib import Path
from typing import List, Optional

from ..base import AbstractExporter
from ....core import ScanConfig, TraversalResult, StandardTreeRenderer
from ....utils import image_renderer, io_processor, FileSystemError, terminal, logger

class TextExporter(AbstractExporter):
    def __init__(self, format_type: str = 'md'):
        self.format_type: str = format_type
        self.tree_renderer: StandardTreeRenderer = StandardTreeRenderer()

    def export(self, target_path: Path, config: ScanConfig, result: TraversalResult, out_file: Path, is_full: bool = False) -> bool:
        lines: List[str] = self.tree_renderer.render(result, config, root_path=target_path)
        
        root_name: str = ""
        if len(target_path.name) > 0:
            root_name = target_path.name
        else:
            root_name = str(target_path)
            
        tree_text: str = f"{root_name}/\n"
        for line in lines:
            tree_text = tree_text + line + "\n"
            
        tree_text = tree_text + f"\n[ {result.stats['dirs']} directories, {result.stats['files']} files | Approx. {result.estimated_tokens} tokens ]"

        if out_file.exists() is True:
            if terminal.prompt_confirmation(f"Target file '{out_file.name}' already exists. Overwrite? [y/n]: ") is False:
                logger.info("Export aborted by user.")
                return False
            
        full_content: str = ""
        if is_full is True:
            full_content = self._aggregate_full_content(result, config)
            if self.format_type == 'image':
                self.format_type = 'md'
                out_file = out_file.with_suffix('.md')

        template_content: str = ""
        if config.template_path is not None:
            if config.template_path.exists() is True:
                read_res: Optional[str] = io_processor.read_text_safely(config.template_path, quiet=False)
                if read_res is not None:
                    template_content = read_res
            
        try:
            if self.format_type == 'md':
                final_text: str = ""
                base_md: str = f"# Directory Structure Stats: `{target_path}`\n\n```text\n{tree_text}\n```\n{full_content}"
                
                if len(template_content) > 0:
                    if "{{SEEDLING_CONTEXT}}" in template_content:
                        final_text = template_content.replace("{{SEEDLING_CONTEXT}}", base_md)
                    else:
                        final_text = template_content + "\n\n" + base_md
                else:
                    final_text = base_md

                with open(out_file, 'w', encoding='utf-8') as f:
                    f.write(final_text)
                return True
                
            elif self.format_type == 'txt':
                final_text = ""
                base_txt: str = tree_text + "\n" + full_content
                
                if len(template_content) > 0:
                    if "{{SEEDLING_CONTEXT}}" in template_content:
                        final_text = template_content.replace("{{SEEDLING_CONTEXT}}", base_txt)
                    else:
                        final_text = template_content + "\n\n" + base_txt
                else:
                    final_text = base_txt
                    
                with open(out_file, 'w', encoding='utf-8') as f:
                    f.write(final_text)
                return True
                
            elif self.format_type == 'image':
                render_result: bool = image_renderer.render_text_to_image(tree_text, out_file, len(lines))
                return render_result
                
        except OSError as err:
            raise FileSystemError(
                message=f"Failed to write exported data to {out_file.name}",
                context={"path": str(out_file)}
            ) from err
            
        return False

    def _aggregate_full_content(self, result: TraversalResult, config: ScanConfig) -> str:
        sections: List[str] = ["\n\n" + "="*60, "FULL PROJECT CONTENT", "="*60 + "\n"]
        for item in result.text_files:
            content: Optional[str] = result.get_content(item, quiet=config.quiet)
            if content is not None:
                fence: str = io_processor.calculate_markdown_fence(content)
                lang: str = ""
                if len(item.path.suffix) > 0:
                    lang = item.path.suffix.lstrip('.')
                    
                sections.append(f"### FILE: {item.relative_path}\n")
                sections.append(f"{fence}{lang}\n")
                sections.append(f"{content}\n")
                sections.append(f"{fence}\n")
                
        final_str: str = ""
        for sec in sections:
            if len(final_str) == 0:
                final_str = sec
            else:
                final_str = final_str + "\n" + sec
                
        return final_str