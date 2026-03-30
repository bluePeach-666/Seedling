from __future__ import annotations
import fnmatch
import difflib
import re
from pathlib import Path
from abc import ABC, abstractmethod
from typing import FrozenSet, List, Optional, Sequence, Final

from .config import ScanConfig
from ..utils import FileSettings, ConfigurationError, SingletonMeta

class AbstractMatcherEngine(ABC):
    @abstractmethod
    def evaluate_exclusion_rules(self, item_path: Path, base_dir: Path, exclude_patterns: Sequence[str]) -> bool:
        pass

    @abstractmethod
    def evaluate_inclusion_rules(self, item_path: Path, base_dir: Path, include_patterns: Sequence[str]) -> bool:
        pass

    @abstractmethod
    def validate_scan_target(self, item: Path, base_dir: Path, config: ScanConfig) -> bool:
        pass

    @abstractmethod
    def fuzzy_match_candidates(self, target: str, candidates: List[str], cutoff: float = 0.7, limit: int = 1) -> List[str]:
        pass

    @abstractmethod
    def evaluate_regex_rule(self, target: str, pattern: str, ignore_case: bool = True) -> bool:
        pass

    @abstractmethod
    def evaluate_exact_rule(self, target: str, keyword: str, ignore_case: bool = True) -> bool:
        pass

    @abstractmethod
    def detect_text_file(self, file_path: Path) -> bool:
        pass

class CoreMatcherEngine(AbstractMatcherEngine, metaclass=SingletonMeta):
    
    def evaluate_exclusion_rules(self, item_path: Path, base_dir: Path, exclude_patterns: Sequence[str]) -> bool:
        rel_path: str = "/" + item_path.relative_to(base_dir).as_posix()
        item_name: str = item_path.name

        for pattern in exclude_patterns:
            is_dir_only: bool = False
            if pattern.endswith('/'):
                is_dir_only = True

            clean_pattern: str = pattern
            if is_dir_only is True:
                clean_pattern = pattern.rstrip('/')

            if clean_pattern.startswith('/'):
                if fnmatch.fnmatch(rel_path, clean_pattern):
                    if is_dir_only is False:
                        return True
                    else:
                        if item_path.is_dir() is True:
                            return True
            else:
                if fnmatch.fnmatch(item_name, clean_pattern):
                    if is_dir_only is False:
                        return True
                    else:
                        if item_path.is_dir() is True:
                            return True
                            
                if fnmatch.fnmatch(rel_path, f"*/{clean_pattern}"):
                    if is_dir_only is False:
                        return True
                    else:
                        if item_path.is_dir() is True:
                            return True
                            
                if fnmatch.fnmatch(rel_path, f"*/{clean_pattern}/*"):
                    if is_dir_only is False:
                        return True
                    else:
                        if item_path.is_dir() is True:
                            return True
                            
                if fnmatch.fnmatch(rel_path, f"**/{clean_pattern}"):
                    if is_dir_only is False:
                        return True
                    else:
                        if item_path.is_dir() is True:
                            return True
                            
        return False

    def evaluate_inclusion_rules(self, item_path: Path, base_dir: Path, include_patterns: Sequence[str]) -> bool:
        if len(include_patterns) == 0:
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
            except ValueError:
                pass
            except TypeError:
                pass

            rel_str: str = rel_path.as_posix()
            
            if fnmatch.fnmatch(rel_str, clean):
                return True
            else:
                if fnmatch.fnmatch(rel_str, f"*/{clean}"):
                    return True
                
        return False

    def validate_scan_target(self, item: Path, base_dir: Path, config: ScanConfig) -> bool:
        if config.show_hidden is False:
            if item.name.startswith('.'):
                return False
                
        if self.evaluate_exclusion_rules(item, base_dir, config.excludes) is True:
            return False
            
        if len(config.includes) > 0:
            if item.is_file() is True:
                if self.evaluate_inclusion_rules(item, base_dir, config.includes) is False:
                    return False
                    
        if config.file_type is not None:
            if item.is_file() is True:
                allowed_extensions: Optional[FrozenSet[str]] = FileSettings.FILE_TYPE_MAP.get(config.file_type.lower())
                if allowed_extensions is not None:
                    if item.suffix.lower() not in allowed_extensions:
                        return False
                        
        if config.text_only is True:
            if item.is_file() is True:
                if self.detect_text_file(item) is False:
                    return False
                    
        return True

    def fuzzy_match_candidates(self, target: str, candidates: List[str], cutoff: float = 0.7, limit: int = 1) -> List[str]:
        if len(target) == 0:
            return []

        if len(candidates) == 0:
            return []
            
        matched_results: List[str] = difflib.get_close_matches(
            word=target, 
            possibilities=candidates, 
            n=limit, 
            cutoff=cutoff
        )
        
        return matched_results

    def evaluate_regex_rule(self, target: str, pattern: str, ignore_case: bool = True) -> bool:
        if len(target) == 0:
            return False
            
        if len(pattern) == 0:
            return False

        flags: int = 0
        if ignore_case is True:
            flags = re.IGNORECASE

        try:
            compiled_pattern: re.Pattern[str] = re.compile(pattern, flags)
            match_result: Optional[re.Match[str]] = compiled_pattern.search(target)
            
            if match_result is not None:
                return True
            else:
                return False
                
        except re.error as err:
            raise ConfigurationError(
                message=f"Invalid regular expression pattern: '{pattern}'",
                hint="Please verify the syntax of your regex.",
                context={"error": str(err), "pattern": pattern}
            ) from err

    def evaluate_exact_rule(self, target: str, keyword: str, ignore_case: bool = True) -> bool:
        if len(target) == 0:
            return False
            
        if len(keyword) == 0:
            return False

        if ignore_case is True:
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
                
    def detect_text_file(self, file_path: Path) -> bool:
        filename_lower: str = file_path.name.lower()
        suffix_lower: str = file_path.suffix.lower()

        if suffix_lower in FileSettings.TEXT_EXTENSIONS:
            return True
            
        if filename_lower in FileSettings.SPECIAL_TEXT_NAMES:
            return True     
            
        if filename_lower.startswith('.'):
            if len(suffix_lower) == 0:
                return True        
                
        return False

matcher_engine: Final[AbstractMatcherEngine] = CoreMatcherEngine()