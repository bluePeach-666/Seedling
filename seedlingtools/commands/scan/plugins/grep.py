from __future__ import annotations
import re
import json
from pathlib import Path
from typing import List, Callable, Any, Dict
from dataclasses import dataclass
from ..base import AbstractScanPlugin
from ....core import ScanConfig, TraversalResult
from ....utils import logger, FileSystemError, ConfigurationError

@dataclass
class GrepMatch:
    """搜索匹配命中实体结构"""
    file_path: Path
    relative_path: Path
    line_number: int
    line_content: str
    context_before: List[str]
    context_after: List[str]


class GrepPlugin(AbstractScanPlugin):
    """基于纯文本与正则表达式的全文内容检索插件"""

    def __init__(self, pattern: str, context_lines: int = 0, ignore_case: bool = False, format_type: str = 'md') -> None:
        self.pattern: str = pattern
        self.context_lines: int = context_lines
        self.ignore_case: bool = ignore_case
        self.format_type: str = format_type

    def execute(self, target_path: Path, config: ScanConfig, result: TraversalResult, **kwargs: Any) -> None:
        if not self.pattern:
            raise ConfigurationError(
                message="Grep search pattern cannot be empty.",
                hint="Provide a valid string or regex pattern via CLI arguments."
            )

        out_file: Path = kwargs.get('out_file', Path.cwd() / f"{target_path.name}_grep.{self.format_type}")
        
        logger.info(f"Executing search for pattern: '{self.pattern}'")
        matches: List[GrepMatch] = self._search_contents(result, config)

        if not matches:
            logger.info("No matches found in the scanned files.")
            return

        unique_files: int = len(set(m.file_path for m in matches))
        logger.info(f"Found {len(matches)} matches in {unique_files} files.")
        
        # 打印到控制台预览
        print(self._format_text_output(matches))
        
        # 持久化输出
        self._save_results(matches, target_path, unique_files, out_file)

    def _search_contents(self, result: TraversalResult, config: ScanConfig) -> List[GrepMatch]:
        matches: List[GrepMatch] = []
        regex_flags: int = re.IGNORECASE if self.ignore_case else 0
        
        if config.use_regex:
            try:
                compiled = re.compile(self.pattern, regex_flags)
                matcher: Callable[[str], bool] = lambda line: bool(compiled.search(line))
            except re.error as err:
                raise ConfigurationError(
                    message=f"Failed to compile regular expression: {err}",
                    hint="Check your regex syntax.",
                    context={"pattern": self.pattern}
                ) from err
        else:
            if self.ignore_case:
                pattern_lower: str = self.pattern.lower()
                matcher = lambda line: pattern_lower in line.lower()
            else:
                matcher = lambda line: self.pattern in line

        for item in result.text_files:
            content: str | None = result.get_content(item, quiet=config.quiet)
            if not content:
                continue
                
            lines: List[str] = content.split('\n')
            for i, line in enumerate(lines):
                if matcher(line):
                    start: int = max(0, i - self.context_lines)
                    end: int = min(len(lines), i + self.context_lines + 1)
                    matches.append(GrepMatch(
                        file_path=item.path,
                        relative_path=item.relative_path,
                        line_number=i + 1,
                        line_content=line,
                        context_before=lines[start:i],
                        context_after=lines[i + 1:end]
                    ))

        return matches

    def _format_text_output(self, matches: List[GrepMatch]) -> str:
        lines: List[str] = []
        for m in matches:
            if self.context_lines > 0 and m.context_before:
                for i, ctx in enumerate(m.context_before):
                    lines.append(f"  {m.line_number - len(m.context_before) + i}-\t{ctx}")
                    
            lines.append(f">>> {m.relative_path}:{m.line_number}\t{m.line_content}")
            
            if self.context_lines > 0 and m.context_after:
                for i, ctx in enumerate(m.context_after):
                    lines.append(f"  {m.line_number + i + 1}-\t{ctx}")
        return "\n".join(lines)

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
        payload: Dict[str, Any] = {
            "pattern": self.pattern,
            "case_sensitive": not self.ignore_case,
            "target": str(target_path),
            "total_matches": len(matches),
            "files_matched": unique_files,
            "matches": [
                {
                    "file": str(m.relative_path),
                    "line": m.line_number,
                    "content": m.line_content,
                    "context_before": m.context_before,
                    "context_after": m.context_after
                }
                for m in matches
            ]
        }
        with open(out_file, 'w', encoding='utf-8') as f:
            json.dump(payload, f, indent=2, ensure_ascii=False)

    def _write_markdown(self, matches: List[GrepMatch], target_path: Path, unique_files: int, out_file: Path) -> None:
        mode_str: str = 'Case-insensitive' if self.ignore_case else 'Case-sensitive'
        with open(out_file, 'w', encoding='utf-8') as f:
            f.write(f"# Grep Results: `{self.pattern}`\n\n")
            f.write(f"**Target**: `{target_path}`\n\n")
            f.write(f"**Mode**: {mode_str}\n\n")
            f.write(f"**Stats**: {len(matches)} matches in {unique_files} files\n\n")
            f.write("```text\n")
            f.write(self._format_text_output(matches))
            f.write("\n```\n")