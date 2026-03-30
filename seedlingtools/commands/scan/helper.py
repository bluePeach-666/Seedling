from __future__ import annotations
from pathlib import Path
import sys
from typing import List, Optional, FrozenSet

from ...core import matcher_engine
from ...utils import logger, terminal, io_processor, FileSettings

def intercept_garbage_files(
    target_path: Path, 
    current_excludes: List[str], 
    is_no_hidden: bool, 
    is_explicit_ignore: bool,
    file_type: Optional[str] = None,
    is_search_only: bool = False
) -> List[str]:
    raw_garbage_items: List[Path] = []
    try:
        for item in target_path.iterdir():
            for pattern in FileSettings.GARBAGE_PATTERNS:
                if item.name == pattern:
                    raw_garbage_items.append(item)
                    break
    except OSError:
        return current_excludes

    if len(raw_garbage_items) == 0:
        return current_excludes

    leaking_garbage: List[str] = []
    for item_path in raw_garbage_items:
        name: str = item_path.name
        is_leaking: bool = True
        
        if is_no_hidden is True:
            if name.startswith('.') is True:
                is_leaking = False
                
        if is_leaking is True:
            if matcher_engine.evaluate_exclusion_rules(item_path, target_path, current_excludes) is True:
                is_leaking = False
                
        if is_leaking is True:
            if file_type is not None:
                if item_path.is_file() is True:
                    type_lower: str = file_type.lower()
                    if type_lower in FileSettings.FILE_TYPE_MAP:
                        allowed: Optional[FrozenSet[str]] = FileSettings.FILE_TYPE_MAP[type_lower]
                        if allowed is not None:
                            if item_path.suffix.lower() not in allowed:
                                is_leaking = False
                                
        if is_leaking is True:
            leaking_garbage.append(name)

    if len(leaking_garbage) == 0:
        return current_excludes

    has_explicit_intent: bool = False
    if is_no_hidden is True:
        has_explicit_intent = True
    else:
        if is_explicit_ignore is True:
            has_explicit_intent = True

    is_interactive: bool = False
    if sys.stdin.isatty() is True:
        if sys.stdout.isatty() is True:
            is_interactive = True
            
    gitignore_path: Path = target_path / ".gitignore"
    garbage_names_str: str = ", ".join(leaking_garbage)
    warning_msg: str = f"Project clutter detected: {garbage_names_str}"

    if is_interactive is False:
        logger.warning(warning_msg)
        if gitignore_path.exists() is True:
            logger.info("Advice: .gitignore found. Use '-e' to apply rules in non-interactive mode.")
        return current_excludes

    if is_search_only is True:
        logger.warning(warning_msg)
        return current_excludes
        
    if has_explicit_intent is True:
        logger.warning(warning_msg)
        return current_excludes
    
    logger.warning(warning_msg)
    if gitignore_path.exists() is True:
        prompt: str = "A .gitignore file was found. Use it to filter these items? [y/n]: "
        if terminal.prompt_confirmation(prompt, default_no=False) is True:
            _read_ignore_rules(gitignore_path, current_excludes)
            return current_excludes
    else:
        logger.info("Advice: Use '--nohidden' or create a '.gitignore' to clean up your scan.")
            
    return current_excludes


def expand_scan_excludes(raw_excludes: List[str]) -> List[str]:
    expanded_excludes: List[str] = []
    cwd: Path = Path.cwd()
    
    for item in raw_excludes:
        item_path: Path = Path(item).expanduser()
        
        if item_path.is_file() is True:
            is_safe: bool = io_processor.validate_path_security(item_path, cwd)
            should_read: bool = True
            
            if is_safe is False:
                prompt_safe: str = f"File '{item}' is outside current directory. Read as rules? [y/n]: "
                if terminal.prompt_confirmation(prompt_safe, default_no=True) is False:
                    should_read = False
            else:
                item_lower_check: str = item.lower()
                if "ignore" not in item_lower_check:
                    if "." not in item:
                        prompt_read: str = f"Treat file '{item}' as a list of exclusion rules? [y/n]: "
                        if terminal.prompt_confirmation(prompt_read, default_no=False) is False:
                            should_read = False

            if should_read is True:
                _read_ignore_rules(item_path, expanded_excludes)
            else:
                expanded_excludes.append(item.replace('\\', '/'))
                
        else:
            item_lower_search: str = item.lower()
            if "ignore" in item_lower_search:
                try:
                    possible_files: List[Path] = []
                    for f in cwd.iterdir():
                        if f.is_file() is True:
                            f_name_lower: str = f.name.lower()
                            is_match: bool = False
                            
                            if item_lower_search in f_name_lower:
                                is_match = True
                            else:
                                if "ignore" in f_name_lower:
                                    is_match = True
                                    
                            if is_match is True:
                                possible_files.append(f)
                    
                    if len(possible_files) > 0:
                        guess_file: Path = possible_files[0]
                        prompt_guess: str = f"Could not find '{item}', but found '{guess_file.name}'. Use it as rules? [y/n]: "
                        if terminal.prompt_confirmation(prompt_guess, default_no=True) is True:
                            _read_ignore_rules(guess_file, expanded_excludes)
                            continue
                except OSError:
                    pass
                
                expanded_excludes.append(item.replace('\\', '/'))
            else:
                clean_item: str = item.replace('\\', '/').strip()
                if len(clean_item) > 0:
                    expanded_excludes.append(clean_item)
                
    return expanded_excludes


def _read_ignore_rules(file_path: Path, rules_list: List[str]) -> None:
    logger.info(f"Loading exclusion rules from: {file_path.name}")
    try:
        content: Optional[str] = io_processor.read_text_safely(file_path, quiet=True)
        if content is not None:
            lines: List[str] = content.splitlines()
            for line in lines:
                clean_line: str = line.strip()
                if len(clean_line) > 0:
                    if clean_line.startswith("#") is False:
                        normalized_rule: str = clean_line.replace('\\', '/').strip()
                        rules_list.append(normalized_rule)
    except Exception as err:
        logger.error(f"Failed to parse rule file {file_path.name}: {err}")