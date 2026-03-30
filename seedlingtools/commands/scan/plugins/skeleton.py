from __future__ import annotations
import ast
import sys
from pathlib import Path
from typing import Any, List, Optional

from ..base import AbstractScanPlugin
from ....core import ScanConfig, TraversalResult
from ....utils import logger, SystemProbeError, FileSystemError

class SkeletonTransformer(ast.NodeTransformer):
    def _strip_body(self, node: Any) -> Any:
        docstring: Optional[str] = ast.get_docstring(node)
        
        if docstring is not None:
            node.body = [node.body[0], ast.Expr(value=ast.Constant(value=...))]
        else:
            node.body = [ast.Expr(value=ast.Constant(value=...))]
            
        return node

    def visit_FunctionDef(self, node: Any) -> Any: 
        stripped_node: Any = self._strip_body(node)
        return self.generic_visit(stripped_node)
        
    def visit_AsyncFunctionDef(self, node: Any) -> Any: 
        stripped_node: Any = self._strip_body(node)
        return self.generic_visit(stripped_node)

class SkeletonPlugin(AbstractScanPlugin):
    def __init__(self) -> None:
        if hasattr(ast, "unparse") is False:
            raise SystemProbeError(
                message=f"Skeleton extraction requires Python 3.9+ (current: {sys.version_info.major}.{sys.version_info.minor})"
            )

    def execute(self, target_path: Path, config: ScanConfig, result: TraversalResult, **kwargs: Any) -> None:
        out_file: Path
        if 'out_file' in kwargs:
            out_file = kwargs['out_file']
        else:
            out_file = Path.cwd() / f"{target_path.name}_skeleton.md"
            
        sections: List[str] = ["\n\n" + "="*60, "PROJECT CODE SKELETON", "="*60 + "\n"]
        py_files_processed: int = 0

        for item in result.text_files:
            if item.path.suffix.lower() == '.py':
                content: Optional[str] = result.get_content(item, quiet=True)
                if content is not None:
                    skeleton_code: str = self._extract_skeleton(content)
                    sections.append(f"### FILE: {item.relative_path}\n```python\n{skeleton_code}\n```\n")
                    py_files_processed += 1

        if py_files_processed == 0:
            logger.warning("No valid Python (.py) files found in the target directory.")
            return

        try:
            with open(out_file, 'w', encoding='utf-8') as f:
                for section in sections:
                    f.write(section)
                    
            logger.info(f"Successfully extracted skeleton from {py_files_processed} Python files.")
        except OSError as err:
            raise FileSystemError(
                message=f"Failed to save skeleton file.",
                context={"error": str(err)}
            ) from err

    def _extract_skeleton(self, code: str) -> str:
        try:
            tree: ast.Module = ast.parse(code)
            transformer: SkeletonTransformer = SkeletonTransformer()
            modified_tree: ast.AST = transformer.visit(tree)
            ast.fix_missing_locations(modified_tree) 
            return ast.unparse(modified_tree) # type: ignore
        except SyntaxError as err:
            logger.debug(f"AST Syntax error during extraction: {err}")
            return code