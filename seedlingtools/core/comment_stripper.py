from __future__ import annotations
import ast
import io
import tokenize
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Final, Optional, Sequence, Tuple

from ..utils import ConfigurationError, FileSystemError, io_processor


SUPPORTED_INLINE_EXTENSIONS: Final[Tuple[str, ...]] = (".py", ".js", ".ts", ".tsx", ".jsx", ".c", ".h", ".cpp", ".hpp")
PYTHON_EXTENSIONS: Final[Tuple[str, ...]] = (".py",)


@dataclass(frozen=True)
class StripCommentsResult:
    original_text: str
    stripped_text: str
    original_tokens: int
    stripped_tokens: int

    @property
    def saved_tokens(self) -> int:
        return self.original_tokens - self.stripped_tokens

    @property
    def saved_percent(self) -> float:
        if self.original_tokens <= 0:
            return 0.0
        return (self.saved_tokens / self.original_tokens) * 100.0


class CommentStripper:
    def strip_file(self, file_path: Path) -> StripCommentsResult:
        source_text: Optional[str] = io_processor.read_text_safely(file_path, quiet=False)
        if source_text is None:
            raise FileSystemError(
                message=f"Failed to read text file for comment stripping: {file_path.name}",
                context={"path": str(file_path)}
            )

        suffix: str = file_path.suffix.lower()
        if suffix in PYTHON_EXTENSIONS:
            stripped_text = self._strip_python_comments(source_text)
        elif suffix in SUPPORTED_INLINE_EXTENSIONS:
            stripped_text = self._strip_inline_comments(source_text)
        else:
            raise ConfigurationError(
                message=f"Unsupported file type for comment stripping: {file_path.suffix or file_path.name}",
                hint="Use a Python, JS/TS, or C-family text file."
            )

        return StripCommentsResult(
            original_text=source_text,
            stripped_text=stripped_text,
            original_tokens=max(0, len(source_text) // 4),
            stripped_tokens=max(0, len(stripped_text) // 4)
        )

    def strip_mapping(self, contents: Dict[str, str]) -> Dict[str, str]:
        stripped_mapping: Dict[str, str] = {}
        for rel_path, content in contents.items():
            suffix: str = Path(rel_path).suffix.lower()
            if suffix in PYTHON_EXTENSIONS:
                stripped_mapping[rel_path] = self._strip_python_comments(content)
            elif suffix in SUPPORTED_INLINE_EXTENSIONS:
                stripped_mapping[rel_path] = self._strip_inline_comments(content)
            else:
                stripped_mapping[rel_path] = content
        return stripped_mapping

    def _strip_python_comments(self, source_text: str) -> str:
        without_docstrings: str = _strip_python_docstrings(source_text)
        token_stream = tokenize.generate_tokens(io.StringIO(without_docstrings).readline)
        output_tokens = []
        for token in token_stream:
            if token.type == tokenize.COMMENT:
                continue
            output_tokens.append(token)
        stripped_text = tokenize.untokenize(output_tokens)
        return stripped_text.rstrip() + "\n"

    def _strip_inline_comments(self, source_text: str) -> str:
        result_chars = []
        i: int = 0
        length: int = len(source_text)
        in_single_quote: bool = False
        in_double_quote: bool = False
        in_backtick: bool = False
        in_block_comment: bool = False
        in_line_comment: bool = False
        escape_next: bool = False

        while i < length:
            char = source_text[i]
            next_char = source_text[i + 1] if (i + 1) < length else ""

            if in_line_comment is True:
                if char == "\n":
                    in_line_comment = False
                    result_chars.append(char)
                i += 1
                continue

            if in_block_comment is True:
                if char == "*" and next_char == "/":
                    in_block_comment = False
                    i += 2
                else:
                    i += 1
                continue

            if escape_next is True:
                result_chars.append(char)
                escape_next = False
                i += 1
                continue

            if in_single_quote is True:
                result_chars.append(char)
                if char == "\\":
                    escape_next = True
                elif char == "'":
                    in_single_quote = False
                i += 1
                continue

            if in_double_quote is True:
                result_chars.append(char)
                if char == "\\":
                    escape_next = True
                elif char == '"':
                    in_double_quote = False
                i += 1
                continue

            if in_backtick is True:
                result_chars.append(char)
                if char == "\\":
                    escape_next = True
                elif char == "`":
                    in_backtick = False
                i += 1
                continue

            if char == "/" and next_char == "/":
                in_line_comment = True
                i += 2
                continue

            if char == "/" and next_char == "*":
                in_block_comment = True
                i += 2
                continue

            if char == "'":
                in_single_quote = True
                result_chars.append(char)
                i += 1
                continue

            if char == '"':
                in_double_quote = True
                result_chars.append(char)
                i += 1
                continue

            if char == "`":
                in_backtick = True
                result_chars.append(char)
                i += 1
                continue

            result_chars.append(char)
            i += 1

        return "".join(result_chars).rstrip() + "\n"


def _strip_python_docstrings(source_text: str) -> str:
    try:
        tree = ast.parse(source_text)
    except SyntaxError:
        return source_text

    docstring_ranges = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) is False:
            continue
        if len(node.body) == 0:
            continue
        first_stmt = node.body[0]
        if isinstance(first_stmt, ast.Expr) is False:
            continue
        if isinstance(first_stmt.value, ast.Constant) is False:
            continue
        if isinstance(first_stmt.value.value, str) is False:
            continue
        if hasattr(first_stmt, "lineno") is False or hasattr(first_stmt, "end_lineno") is False:
            continue
        if hasattr(first_stmt, "col_offset") is False or hasattr(first_stmt, "end_col_offset") is False:
            continue
        docstring_ranges.append((
            first_stmt.lineno,
            first_stmt.col_offset,
            first_stmt.end_lineno,
            first_stmt.end_col_offset
        ))

    if len(docstring_ranges) == 0:
        return source_text

    lines = source_text.splitlines(keepends=True)
    line_offsets = [0]
    total = 0
    for line in lines:
        total += len(line)
        line_offsets.append(total)

    mutable_text = source_text
    spans = []
    for start_line, start_col, end_line, end_col in docstring_ranges:
        start_index = line_offsets[start_line - 1] + start_col
        end_index = line_offsets[end_line - 1] + end_col
        spans.append((start_index, end_index))

    for start_index, end_index in sorted(spans, reverse=True):
        mutable_text = mutable_text[:start_index] + mutable_text[end_index:]

    return mutable_text
