from __future__ import annotations
import shutil
import re
from abc import ABC, abstractmethod
from pathlib import Path, PureWindowsPath
from typing import Any, Dict, List, Optional, Final, Tuple
from .sysinfo import is_relative_to_compat
from .log_helper import logger
from .exceptions import FileSystemError
from .constants import FileSettings

class AbstractIOProcessor(ABC):
    """文件系统输入输出处理的抽象接口"""

    @abstractmethod
    def validate_path_security(self, path: Path, base_dir: Path) -> bool:
        """校验目标路径是否安全地处于基础目录边界内"""
        pass

    @abstractmethod
    def calculate_markdown_fence(self, content: str) -> str:
        """计算转义所需的最优 Markdown 代码块边界符号"""
        pass

    @abstractmethod
    def parse_directory_tree(self, file_path: Path) -> List[str]:
        """从标准文本文件中提取目录树结构"""
        pass

    @abstractmethod
    def deserialize_fenced_blocks(self, file_path: Path) -> Dict[str, str]:
        """解析并提取标准结构化文档中的文件内容块"""
        pass

    @abstractmethod
    def delete_path(self, path: Path) -> None:
        """删除路径操作"""
        pass

    @abstractmethod
    def probe_binary_signature(self, file_path: Path) -> bool:
        """基于文件头的字节码特征进行深度二进制探测"""
        pass

    @abstractmethod
    def read_text_safely(self, file_path: Path, quiet: bool = False) -> Optional[str]:
        """安全的文本读取策略，处理编码降级与二进制拦截"""
        pass

    @abstractmethod
    def write_text_safely(self, file_path: Path, content: str) -> None:
        """安全的文本写入策略，统一异常拦截"""
        pass

    @abstractmethod
    def parse_tree_topology(self, tree_lines: List[str]) -> List[Dict[str, Any]]:
        """将原始文本行解析为结构化的树状拓扑字典列表"""
        pass

    @abstractmethod
    def compare_file_content(self, path: Path, expected_content: str) -> bool:
        """比较磁盘文件内容与预期字符串是否不一致"""
        pass

class LocalFileSystemIO(AbstractIOProcessor):
    """基于本地文件系统的 IO 处理实现类"""

    def validate_path_security(self, path: Path, base_dir: Path) -> bool:
        try:
            p_resolved: Path = path.resolve()
            base_resolved: Path = base_dir.resolve()
            return is_relative_to_compat(p_resolved, base_resolved)
        except (OSError, RuntimeError, ValueError):
            return False

    def calculate_markdown_fence(self, content: str) -> str:
        max_ticks: int = 2
        for line in content.split('\n'):
            stripped: str = line.strip()
            if stripped.startswith('`'):
                ticks: int = len(stripped) - len(stripped.lstrip('`'))
                if ticks > max_ticks:
                    max_ticks = ticks
        return '`' * (max_ticks + 1)

    def parse_directory_tree(self, file_path: Path) -> List[str]:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines: List[str] = f.readlines()
        except OSError as err:
            raise FileSystemError(
                message=f"Failed to read tree blueprint: {file_path.name}",
                context={"path": str(file_path)}
            ) from err

        tree_lines: List[str] = []
        in_tree: bool = False
        tree_chars: Final[Tuple[str, ...]] = ('├──', '└──', '│')

        for i, line in enumerate(lines):
            stripped: str = line.rstrip()
            if not stripped:
                if in_tree:
                    break
                else:
                    continue
                
            has_tree_chars: bool = any(c in line for c in tree_chars)
            next_has_tree_chars: bool = False
            
            if i + 1 < len(lines):
                next_has_tree_chars = any(c in lines[i+1] for c in tree_chars)
                
            if has_tree_chars:
                in_tree = True
                if not stripped.startswith('```'): 
                    tree_lines.append(stripped)
            else:
                if not in_tree:
                    if next_has_tree_chars:
                        in_tree = True
                        if not stripped.startswith('```'): 
                            tree_lines.append(stripped)
                else:
                    if stripped.startswith('```'):
                        break
                    else:
                        break
                    
        return tree_lines

    def deserialize_fenced_blocks(self, file_path: Path) -> Dict[str, str]:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines: List[str] = f.readlines()
        except OSError as err:
            raise FileSystemError(f"Failed to read content payload: {file_path.name}") from err

        file_contents: Dict[str, str] = {}
        current_file: Optional[str] = None
        current_content: List[str] = []
        fence_stack: List[str] = [] 

        for line in lines:
            stripped: str = line.strip()

            if not current_file:
                if stripped.startswith('### FILE: '):
                    raw_path: str = stripped.replace('### FILE: ', '').strip()
                    current_file = PureWindowsPath(raw_path).as_posix()
                    current_content = [] 
                    continue

            if current_file:
                match: Optional[re.Match[str]] = re.match(r'^(`{3,})', stripped)
                
                if not fence_stack:
                    if match:
                        fence_stack.append(match.group(1))
                    continue
                
                if match:
                    ticks: str = match.group(1)
                    if ticks == fence_stack[-1]:
                        if len(stripped) == len(ticks):
                            fence_stack.pop()
                            if not fence_stack:
                                file_contents[current_file] = "".join(current_content).rstrip('\n') + '\n'
                                current_file = None
                                continue
                            else:
                                current_content.append(line)
                        else:
                            fence_stack.append(ticks)
                            current_content.append(line)
                    else:
                        fence_stack.append(ticks)
                        current_content.append(line)
                else:
                    current_content.append(line)

        return file_contents
    
    def delete_path(self, path: Path) -> None:
        try:
            if path.is_file():
                path.unlink()
            elif path.is_symlink():
                path.unlink()
            elif path.is_dir():
                shutil.rmtree(path)
        except OSError as err:
            raise FileSystemError(
                message=f"Failed to delete path: {path.name}",
                hint="Check file permissions or if the file is currently locked.",
                context={"path": str(path)}
            ) from err

    def probe_binary_signature(self, file_path: Path) -> bool:
        try:
            with open(file_path, 'rb') as f:
                chunk: bytes = f.read(FileSettings.PROBE_CHUNK_SIZE)
                
                if b'\x00' in chunk:
                    return True
                    
                for sig in FileSettings.BINARY_SIGNATURES:
                    if chunk.startswith(sig):
                        return True
                        
        except OSError as err:
            logger.debug(f"Binary probe downgraded for {file_path.name} due to IO constraint: {err}")
            return True
            
        return False

    def read_text_safely(self, file_path: Path, quiet: bool = False) -> Optional[str]:
        if self.probe_binary_signature(file_path):
            return None

        encodings: Tuple[str, ...] = ('utf-8', 'gbk', 'big5', 'utf-16', 'latin-1')
        
        for enc in encodings:
            try:
                with open(file_path, 'r', encoding=enc, errors='strict') as f:
                    return f.read()
            except (UnicodeDecodeError, LookupError):
                continue 
            except OSError as err:
                if not quiet:
                    logger.debug(f"IO failure while reading {file_path.name}: {err}")
                return None

        if not quiet:
            logger.warning(f"Skipped {file_path.name}: Unsupported character encoding.")
            
        return None

    def write_text_safely(self, file_path: Path, content: str) -> None:
        try:
            if not file_path.parent.exists():
                file_path.parent.mkdir(parents=True, exist_ok=True)
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
        except OSError as err:
            raise FileSystemError(
                message=f"Failed to write text to: {file_path.name}",
                hint="Verify disk permissions or ensure adequate storage space.",
                context={"path": str(file_path)}
            ) from err

    def parse_tree_topology(self, tree_lines: List[str]) -> List[Dict[str, Any]]:
        raw_items: List[Dict[str, Any]] = []
        
        for line in tree_lines:
            match: Optional[re.Match[str]] = re.match(r'^([│├└─\s]*)(.+)$', line)
            if not match:
                continue
                
            prefix: str = match.group(1)
            content: str = match.group(2)
            
            clean_prefix: str = prefix.replace('│', ' ').replace('├', ' ').replace('└', ' ').replace('─', ' ')
            depth: int = len(clean_prefix) // 4
            
            content_parts: List[str] = content.split('<-')
            clean_name: str = content_parts[0].strip()
            
            name_parts: List[str] = re.split(r'\s{2,}#', clean_name)
            clean_name = name_parts[0].strip()
            
            is_dir: bool = False
            
            if clean_name.endswith('/'):
                is_dir = True
                clean_name = clean_name.rstrip('/')
                
            if clean_name:
                if clean_name != '.':
                    if clean_name != '..':
                        item_dict: Dict[str, Any] = {
                            'depth': depth, 
                            'name': clean_name, 
                            'is_dir': is_dir
                        }
                        raw_items.append(item_dict)

        item_count: int = len(raw_items)
        for i in range(item_count - 1):
            current_depth: int = raw_items[i]['depth']
            next_depth: int = raw_items[i + 1]['depth']
            
            if next_depth > current_depth:
                raw_items[i]['is_dir'] = True
        
        return raw_items
    
    def compare_file_content(self, path: Path, expected_content: str) -> bool:
        if not path.exists():
            return True

        if not path.is_file():
            return True

        actual_content: Optional[str] = self.read_text_safely(path, quiet=True)
        
        if actual_content is None:
            return True
            
        if actual_content != expected_content:
            return True
            
        return False

io_processor: Final[AbstractIOProcessor] = LocalFileSystemIO()
"""全局文件 IO 单例"""