from __future__ import annotations
import fnmatch
import difflib
from pathlib import Path
import re
from typing import FrozenSet, List, Optional, Sequence
from .config import ScanConfig
from ..utils import FileSettings, ConfigurationError, io_processor

def evaluate_exclusion_rules(
    item_path: Path, 
    base_dir: Path, 
    exclude_patterns: Sequence[str]
) -> bool:
    """
    评估目标路径是否触发了排除规则，支持类似 Git 的路径通配符匹配。  
    Args:
        item_path (Path): 待评估的目标文件或目录路径。
        base_dir (Path): 扫描的基础根目录，用于计算相对路径。
        exclude_patterns (Sequence[str]): 排除规则的通配符字符串集合。  
    Returns:
        bool: 如果命中排除规则则返回 True。
    """
    rel_path: str = "/" + item_path.relative_to(base_dir).as_posix()
    item_name: str = item_path.name

    for pattern in exclude_patterns:
        is_dir_only: bool = pattern.endswith('/')
        clean_pattern: str = pattern.rstrip('/')

        if clean_pattern.startswith('/'):
            if fnmatch.fnmatch(rel_path, clean_pattern):
                if not is_dir_only:
                    return True
                else:
                    if item_path.is_dir():
                        return True
        else:
            if fnmatch.fnmatch(item_name, clean_pattern):
                if not is_dir_only:
                    return True
                else:
                    if item_path.is_dir():
                        return True
                    
            if fnmatch.fnmatch(rel_path, f"*/{clean_pattern}"):
                if not is_dir_only:
                    return True
                else:
                    if item_path.is_dir():
                        return True
                    
            if fnmatch.fnmatch(rel_path, f"*/{clean_pattern}/*"):
                if not is_dir_only:
                    return True
                else:
                    if item_path.is_dir():
                        return True
                    
            if fnmatch.fnmatch(rel_path, f"**/{clean_pattern}"):
                if not is_dir_only:
                    return True
                else:
                    if item_path.is_dir():
                        return True
                    
    return False


def evaluate_inclusion_rules(
    item_path: Path, 
    base_dir: Path, 
    include_patterns: Sequence[str]
) -> bool:
    """
    评估目标路径是否符合白名单包含规则。  
    Args:
        item_path (Path): 待评估的目标文件或目录路径。
        base_dir (Path): 扫描的基础根目录，用于计算相对路径。
        include_patterns (Sequence[str]): 包含规则的通配符字符串集合。  
    Returns:
        bool: 如果符合包含规则或白名单为空返回 True。
    """
    if not include_patterns:
        return True

    rel_path: Path = item_path.relative_to(base_dir)
    item_name: str = item_path.name 

    for pattern in include_patterns:
        clean: str = pattern.lstrip('/')

        if fnmatch.fnmatch(item_name, clean):
            return True

        try:
            if rel_path.match(pattern):
                return True
            else:
                if rel_path.match(clean):
                    return True
                
            if pattern.startswith('**/'):
                if rel_path.match(pattern[3:]):
                    return True
        except (ValueError, TypeError):
            pass

        rel_str: str = rel_path.as_posix()
        
        if fnmatch.fnmatch(rel_str, clean):
            return True
        else:
            if fnmatch.fnmatch(rel_str, f"*/{clean}"):
                return True
            
    return False

def validate_scan_target(
    item: Path, 
    base_dir: Path, 
    config: ScanConfig
) -> bool:
    """
    综合评估目标项目是否应被纳入最终的扫描结果。  
    Args:
        item (Path): 待评估的目标项目路径。
        base_dir (Path): 扫描的基础根目录。
        config (ScanConfig): 当前的全局扫描配置对象。
    Returns:
        bool: 如果目标允许被扫描和记录则返回 True。
    """
    
    if not config.show_hidden:
        if item.name.startswith('.'):
            return False
        
    if evaluate_exclusion_rules(item, base_dir, config.excludes):
        return False
        
    if config.includes:
        if item.is_file():
            if not evaluate_inclusion_rules(item, base_dir, config.includes):
                return False
            
    if config.file_type:
        if item.is_file():
            allowed_extensions: Optional[FrozenSet[str]] = FileSettings.FILE_TYPE_MAP.get(config.file_type.lower())
            if allowed_extensions is not None:
                if item.suffix.lower() not in allowed_extensions:
                    return False
                
    if config.text_only:
        if item.is_file():
            if not detect_text_file(item):
                return False
            
    return True

def fuzzy_match_candidates(
    target: str, 
    candidates: List[str], 
    cutoff: float = 0.7, 
    limit: int = 1
) -> List[str]:
    """
    基于字符串相似度的模糊匹配。  
    Args:
        target (str): 需要匹配的目标探测字符串。
        candidates (List[str]): 供匹配的候选字符串全集列表。
        cutoff (float): 相似度置信度阈值。默认值为 0.7。
        limit (int): 允许返回的最大匹配项数量。默认值为 1。  
    Returns:
        List[str]: 达到或超过置信度阈值的候选字符串列表，按相似度从高到低排序。
    """
    if not target:
        return []

    if not candidates:
        return []
        
    matched_results: List[str] = difflib.get_close_matches(
        word=target, 
        possibilities=candidates, 
        n=limit, 
        cutoff=cutoff
    )
    
    return matched_results

def evaluate_regex_rule(target: str, pattern: str, ignore_case: bool = True) -> bool:
    """
    评估目标字符串是否符合正则表达式规则。  
    Args:
        target (str): 待评估的目标字符串。
        pattern (str): 正则表达式模式。
        ignore_case (bool): 是否忽略大小写。默认为 True。     
    Returns:
        bool: 如果正则匹配成功则返回 True。     
    Raises:
        ConfigurationError: 当正则表达式语法无效时抛出。
    """
    if not target:
        return False
        
    if not pattern:
        return False

    flags: int = 0
    if ignore_case:
        flags = re.IGNORECASE

    try:
        compiled_pattern: re.Pattern[str] = re.compile(pattern, flags)
        match_result: Optional[re.Match[str]] = compiled_pattern.search(target)
        
        if match_result:
            return True
        else:
            return False
            
    except re.error as err:
        raise ConfigurationError(
            message=f"Invalid regular expression pattern: '{pattern}'",
            hint="Please verify the syntax of your regex.",
            context={"error": str(err), "pattern": pattern}
        ) from err


def evaluate_exact_rule(target: str, keyword: str, ignore_case: bool = True) -> bool:
    """
    评估目标字符串是否精确包含指定关键字。  
    Args:
        target (str): 待评估的目标字符串。
        keyword (str): 需要查找的关键字。
        ignore_case (bool): 是否忽略大小写。默认为 True。  
    Returns:
        bool: 如果目标字符串包含关键字则返回 True。
    """
    if not target:
        return False
        
    if not keyword:
        return False

    if ignore_case:
        target_lower: str = target.lower()
        keyword_lower: str = keyword.lower()
        if keyword_lower in target_lower:
            return True
        else:
            return False
    else:
        if keyword in target:
            return True
        else:
            return False
        
def detect_text_file(file_path: Path) -> bool:
    """
    基于文件后缀和名称规则进行快速文本文件检测。
    Args:
        file_path (Path): 待检测的目标文件路径。
    Returns:
        bool: 如果被判定为文本文件则返回 True。
    """
    filename_lower: str = file_path.name.lower()
    suffix_lower: str = file_path.suffix.lower()

    if suffix_lower in FileSettings.TEXT_EXTENSIONS:
        return True
        
    if filename_lower in FileSettings.SPECIAL_TEXT_NAMES:
        return True     
        
    if filename_lower.startswith('.'):
        if not suffix_lower:
            return True        
            
    return False

def probe_binary_signature(file_path: Path) -> bool:
    """
    [Deprecated]  
    基于文件头的字节码特征进行深度二进制探测。  
    当前函数仅作为桥接接口保留，所有的实际 I/O 操作均已下发至全局单例 `io_processor` 中进行处理。  
    """
    return io_processor.probe_binary_signature(file_path)