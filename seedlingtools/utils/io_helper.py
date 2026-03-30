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
from .patterns import SingletonMeta

class AbstractIOProcessor(ABC):
    @abstractmethod
    def validate_path_security(self, path: Path, base_dir: Path) -> bool:
        pass

    @abstractmethod
    def calculate_markdown_fence(self, content: str) -> str:
        pass

    @abstractmethod
    def parse_directory_tree(self, file_path: Path) -> List[str]:
        pass

    @abstractmethod
    def deserialize_fenced_blocks(self, file_path: Path) -> Dict[str, str]:
        pass

    @abstractmethod
    def delete_path(self, path: Path) -> None:
        pass

    @abstractmethod
    def probe_binary_signature(self, file_path: Path) -> bool:
        pass

    @abstractmethod
    def read_text_safely(self, file_path: Path, quiet: bool = False) -> Optional[str]:
        pass

    @abstractmethod
    def write_text_safely(self, file_path: Path, content: str) -> None:
        pass

    @abstractmethod
    def parse_tree_topology(self, tree_lines: List[str]) -> List[Dict[str, Any]]:
        pass

    @abstractmethod
    def compare_file_content(self, path: Path, expected_content: str) -> bool:
        pass

class LocalFileSystemIO(AbstractIOProcessor, metaclass=SingletonMeta):
    def validate_path_security(self, path: Path, base_dir: Path) -> bool:
        try:
            p_resolved: Path = path.resolve()
            base_resolved: Path = base_dir.resolve()
            return is_relative_to_compat(p_resolved, base_resolved)
        except OSError:
            return False
        except RuntimeError:
            return False
        except ValueError:
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
        lines: List[str] = []
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
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
            if len(stripped) == 0:
                if in_tree is True:
                    break
                else:
                    continue
                
            has_tree_chars: bool = False
            for c in tree_chars:
                if c in line:
                    has_tree_chars = True
                    break
                    
            next_has_tree_chars: bool = False
            if (i + 1) < len(lines):
                for c in tree_chars:
                    if c in lines[i+1]:
                        next_has_tree_chars = True
                        break
                
            if has_tree_chars is True:
                in_tree = True
                if stripped.startswith('```') is False: 
                    tree_lines.append(stripped)
            else:
                if in_tree is False:
                    if next_has_tree_chars is True:
                        in_tree = True
                        if stripped.startswith('```') is False: 
                            tree_lines.append(stripped)
                else:
                    if stripped.startswith('```'):
                        break
                    else:
                        break
                    
        return tree_lines

    def deserialize_fenced_blocks(self, file_path: Path) -> Dict[str, str]:
        lines: List[str] = []
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
        except OSError as err:
            raise FileSystemError(f"Failed to read content payload: {file_path.name}") from err

        file_contents: Dict[str, str] = {}
        current_file: Optional[str] = None
        current_content: List[str] = []
        fence_stack: List[str] = [] 

        for line in lines:
            stripped: str = line.strip()

            if current_file is None:
                if stripped.startswith('### FILE: '):
                    raw_path: str = stripped.replace('### FILE: ', '').strip()
                    current_file = PureWindowsPath(raw_path).as_posix()
                    current_content = [] 
                continue

            if current_file is not None:
                match: Optional[re.Match[str]] = re.match(r'^(`{3,})', stripped)
                
                if len(fence_stack) == 0:
                    if match is not None:
                        fence_stack.append(match.group(1))
                    continue
                
                if match is not None:
                    ticks: str = match.group(1)
                    if ticks == fence_stack[-1]:
                        if len(stripped) == len(ticks):
                            fence_stack.pop()
                            if len(fence_stack) == 0:
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
            if path.is_file() is True:
                path.unlink()
            elif path.is_symlink() is True:
                path.unlink()
            elif path.is_dir() is True:
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
        if self.probe_binary_signature(file_path) is True:
            return None

        encodings: Tuple[str, ...] = ('utf-8', 'gbk', 'big5', 'utf-16', 'latin-1')
        
        for enc in encodings:
            try:
                with open(file_path, 'r', encoding=enc, errors='strict') as f:
                    return f.read()
            except UnicodeDecodeError:
                continue 
            except LookupError:
                continue
            except OSError as err:
                if quiet is False:
                    logger.debug(f"IO failure while reading {file_path.name}: {err}")
                return None

        if quiet is False:
            logger.warning(f"Skipped {file_path.name}: Unsupported character encoding.")
            
        return None

    def write_text_safely(self, file_path: Path, content: str) -> None:
        try:
            if file_path.parent.exists() is False:
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
            if match is None:
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
                
            if len(clean_name) > 0:
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
        if path.exists() is False:
            return True

        if path.is_file() is False:
            return True

        actual_content: Optional[str] = self.read_text_safely(path, quiet=True)
        
        if actual_content is None:
            return True
            
        if actual_content != expected_content:
            return True
            
        return False

io_processor: Final[AbstractIOProcessor] = LocalFileSystemIO()