import sys
import ast
from pathlib import Path
from seedling.core.logger import logger
from seedling.core.filesystem import get_full_context
from seedling.core.ui import ask_yes_no

class SkeletonTransformer(ast.NodeTransformer):
    def _strip_body(self, node):
        """用 ... 替换复杂的实现逻辑"""
        if ast.get_docstring(node):
            # 如果有文档字符串，保留 body[0]，追加 ...
            node.body = [node.body[0], ast.Expr(value=ast.Constant(value=...))]
        else:
            # 没有文档字符串，直接将整个 body 替换为 ...
            node.body = [ast.Expr(value=ast.Constant(value=...))]
        return node

    def visit_FunctionDef(self, node):
        # 处理普通的 def 函数
        node = self._strip_body(node)
        return self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node):
        # 处理 async def 异步函数
        node = self._strip_body(node)
        return self.generic_visit(node)

def extract_skeleton(code: str) -> str:
    """使用 AST 将 Python 源码转化为骨架"""
    if not hasattr(ast, "unparse"):
        raise EnvironmentError("Skeleton extraction requires Python 3.9+ (ast.unparse).")
        
    try:
        tree = ast.parse(code)
        transformer = SkeletonTransformer()
        modified_tree = transformer.visit(tree)
        ast.fix_missing_locations(modified_tree)
        return ast.unparse(modified_tree)
    except SyntaxError as e:
        logger.warning(f"AST Parse Error: {e}")
        return code # 降级策略：如果发生语法错误，返回原代码，避免程序崩溃
    except Exception as e:
        logger.warning(f"AST Extraction failed: {e}")
        return code

def run_skeleton(args, target_path):
    if not hasattr(ast, "unparse"):
        logger.error("❌ Skeleton extraction requires Python 3.9 or higher (depends on ast.unparse).")
        return

    logger.info(f"\n🦴 Skeleton mode activated! Extracting Python code structure from {target_path}...")
    
    # 复用 get_full_context，但强制开启 text_only 过滤
    context_list = get_full_context(
        target_path, 
        show_hidden=args.show_hidden, 
        excludes=args.exclude,
        text_only=True,
        max_depth=args.depth,
        quiet=args.quiet
    )

    out_dir_path = Path(args.outdir).resolve() if args.outdir else Path.cwd()
    out_dir_path.mkdir(parents=True, exist_ok=True)
    target_name = target_path.name or "root_dir"
    out_name = args.name or f"{target_name}_skeleton.md"
    final_file = out_dir_path / out_name

    # 文件覆盖保护机制
    if final_file.exists():
        logger.warning(f"NOTICE: Target file already exists:\n   👉 {final_file}")
        if not ask_yes_no("Do you want to overwrite it? [y/n]: "):
            logger.info("Operation aborted.")
            return

    sections = ["\n\n" + "="*60, "🦴 PROJECT CODE SKELETON", "="*60 + "\n"]
    py_files_processed = 0

    # 遍历所有文件并执行 AST 骨架提取
    for rel_path, content in context_list:
        if rel_path.suffix.lower() == '.py':
            skeleton_code = extract_skeleton(content)
            sections.append(f"### FILE: {rel_path}")
            sections.append(f"```python\n{skeleton_code}\n```\n")
            py_files_processed += 1

    if py_files_processed == 0:
        logger.warning("🚫 No Python (.py) files found in the target directory.")
        return

    # 写入最终的 Markdown 报告
    try:
        with open(final_file, 'w', encoding='utf-8') as f:
            f.write("\n".join(sections))
        logger.info(f"✅ Successfully extracted skeleton from {py_files_processed} Python files.")
        logger.info(f"🎉 SUCCESS! Skeleton file saved to:\n   👉 {final_file}\n")
    except Exception as e:
        logger.error(f"Failed to save file: {e}")