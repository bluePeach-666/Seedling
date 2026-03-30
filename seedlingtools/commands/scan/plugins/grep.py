from __future__ import annotations
import json
from pathlib import Path
from typing import List, Optional, Any, Dict, Final
from dataclasses import dataclass

from ..base import AbstractScanPlugin
from ....core import ScanConfig, TraversalResult, matcher_engine
from ....utils import logger, FileSystemError, ConfigurationError

@dataclass
class GrepMatch:
    file_path: Path
    relative_path: Path
    line_number: int
    line_content: str
    context_before: List[str]
    context_after: List[str]

class GrepPlugin(AbstractScanPlugin):
    def __init__(self, pattern: str, context_lines: int = 0, ignore_case: bool = False, format_type: str = 'md') -> None:
        self.pattern: Final[str] = pattern
        self.context_lines: Final[int] = context_lines
        self.ignore_case: Final[bool] = ignore_case
        self.format_type: Final[str] = format_type

    def execute(self, target_path: Path, config: ScanConfig, result: TraversalResult, **kwargs: Any) -> None:
        if len(self.pattern) == 0:
            raise ConfigurationError(
                message="Grep search pattern cannot be empty.",
                hint="Provide a valid string or regex pattern via CLI arguments."
            )

        out_file: Path
        if 'out_file' in kwargs:
            out_file = kwargs['out_file']
        else:
            out_file = Path.cwd() / f"{target_path.name}_grep.{self.format_type}"
        
        logger.info(f"Executing search for pattern: '{self.pattern}'")
        matches: List[GrepMatch] = self._search_contents(result, config)

        if len(matches) == 0:
            logger.info("No matches found in the scanned files.")
            return

        unique_files_set: List[Path] = []
        for m in matches:
            if m.file_path not in unique_files_set:
                unique_files_set.append(m.file_path)
        
        unique_files: int = len(unique_files_set)
        logger.info(f"Found {len(matches)} matches in {unique_files} files.")
        
        formatted_text: str = self._format_text_output(matches)
        print(formatted_text)
        
        self._save_results(matches, target_path, unique_files, out_file)

    def _search_contents(self, result: TraversalResult, config: ScanConfig) -> List[GrepMatch]:
        matches: List[GrepMatch] = []
        
        for item in result.text_files:
            content: Optional[str] = result.get_content(item, quiet=config.quiet)
            if content is None:
                continue
                
            lines: List[str] = content.split('\n')
            for i in range(len(lines)):
                line: str = lines[i]
                is_match: bool = False
                
                if config.use_regex is True:
                    is_match = matcher_engine.evaluate_regex_rule(
                        target=line, 
                        pattern=self.pattern, 
                        ignore_case=self.ignore_case
                    )
                else:
                    is_match = matcher_engine.evaluate_exact_rule(
                        target=line, 
                        keyword=self.pattern, 
                        ignore_case=self.ignore_case
                    )
                    
                if is_match is True:
                    start_idx: int = i - self.context_lines
                    if start_idx < 0:
                        start_idx = 0
                        
                    end_idx: int = i + self.context_lines + 1
                    if end_idx > len(lines):
                        end_idx = len(lines)
                        
                    ctx_before: List[str] = []
                    for j in range(start_idx, i):
                        ctx_before.append(lines[j])
                        
                    ctx_after: List[str] = []
                    for k in range(i + 1, end_idx):
                        ctx_after.append(lines[k])
                        
                    match_obj = GrepMatch(
                        file_path=item.path,
                        relative_path=item.relative_path,
                        line_number=i + 1,
                        line_content=line,
                        context_before=ctx_before,
                        context_after=ctx_after
                    )
                    matches.append(match_obj)

        return matches

    def _format_text_output(self, matches: List[GrepMatch]) -> str:
        lines: List[str] = []
        for m in matches:
            if self.context_lines > 0:
                if len(m.context_before) > 0:
                    for i in range(len(m.context_before)):
                        ctx: str = m.context_before[i]
                        lines.append(f"  {m.line_number - len(m.context_before) + i}-\t{ctx}")
                    
            lines.append(f">>> {m.relative_path}:{m.line_number}\t{m.line_content}")
            
            if self.context_lines > 0:
                if len(m.context_after) > 0:
                    for i in range(len(m.context_after)):
                        ctx: str = m.context_after[i]
                        lines.append(f"  {m.line_number + i + 1}-\t{ctx}")
                        
        final_output: str = ""
        for i in range(len(lines)):
            if i == 0:
                final_output = lines[i]
            else:
                final_output = final_output + "\n" + lines[i]
                
        return final_output

    def _save_results(self, matches: List[GrepMatch], target_path: Path, unique_files: int, out_file: Path) -> None:
        try:
            if self.format_type == 'json':
                self._write_json(matches, target_path, unique_files, out_file)
            else:
                self._write_markdown(matches, target_path, unique_files, out_file)
            logger.info(f"Search results exported to: {out_file}")
        except OSError as err:
            raise FileSystemError(
                message=f"Failed to save grep results to {out_file.name}",
                context={"path": str(out_file)}
            ) from err

    def _write_json(self, matches: List[GrepMatch], target_path: Path, unique_files: int, out_file: Path) -> None:
        matches_list: List[Dict[str, Any]] = []
        for m in matches:
            match_dict: Dict[str, Any] = {
                "file": str(m.relative_path),
                "line": m.line_number,
                "content": m.line_content,
                "context_before": m.context_before,
                "context_after": m.context_after
            }
            matches_list.append(match_dict)
            
        is_case_sensitive: bool = False
        if self.ignore_case is False:
            is_case_sensitive = True
            
        payload: Dict[str, Any] = {
            "pattern": self.pattern,
            "case_sensitive": is_case_sensitive,
            "target": str(target_path),
            "total_matches": len(matches),
            "files_matched": unique_files,
            "matches": matches_list
        }
        
        with open(out_file, 'w', encoding='utf-8') as f:
            json.dump(payload, f, indent=2, ensure_ascii=False)

    def _write_markdown(self, matches: List[GrepMatch], target_path: Path, unique_files: int, out_file: Path) -> None:
        mode_str: str = ""
        if self.ignore_case is True:
            mode_str = "Case-insensitive"
        else:
            mode_str = "Case-sensitive"
            
        with open(out_file, 'w', encoding='utf-8') as f:
            f.write(f"# Grep Results: `{self.pattern}`\n\n")
            f.write(f"**Target**: `{target_path}`\n\n")
            f.write(f"**Mode**: {mode_str}\n\n")
            f.write(f"**Stats**: {len(matches)} matches in {unique_files} files\n\n")
            f.write("```text\n")
            
            formatted_output: str = self._format_text_output(matches)
            f.write(formatted_output)
            f.write("\n```\n")