from __future__ import annotations
from pathlib import Path
from typing import List
from ...utils import logger, terminal, io_processor

def _read_ignore_rules(file_path: Path, rules_list: List[str]):
    """从文件中读取并解析过滤规则"""
    logger.info(f"Loading exclusion rules from: {file_path.name}")
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    clean_rule = line.replace('\\', '/').strip()
                    rules_list.append(clean_rule)
    except Exception as e:
        logger.error(f"Failed to read rule file {file_path.name}: {e}")

def expand_scan_excludes(raw_excludes: List[str]) -> List[str]:
    """解析 exclude 参数"""
    expanded_excludes: List[str] = []
    cwd: Path = Path.cwd()
    
    for item in raw_excludes:
        item_path = Path(item).expanduser()
        
        # 场景 A: 这是一个真实存在的物理文件
        if item_path.is_file():
            # 安全校验
            is_safe = io_processor.validate_path_security(item_path, cwd)
            should_read = True
            if not is_safe:
                # 越界文件
                prompt = f"File '{item}' is outside current directory. Read as rules? [y/n]: "
                should_read = terminal.prompt_confirmation(prompt, default_no=True)
            elif 'ignore' not in item.lower() and '.' not in item:
                # 既没 ignore 关键字又没后缀的文件，确认一下是规则还是单纯想排除这个文件
                prompt = f"Treat file '{item}' as a list of exclusion rules? [y/n]: "
                should_read = terminal.prompt_confirmation(prompt, default_no=False)

            if should_read:
                _read_ignore_rules(item_path, expanded_excludes)
            else:
                expanded_excludes.append(item.replace('\\', '/'))
                
        # 场景 B: 路径不存在，但带 ignore 关键字
        elif 'ignore' in item.lower():
            # 在当前目录下找最像的那个文件
            try:
                possible_files = [
                    f for f in cwd.iterdir() 
                    if f.is_file() and (item.lower() in f.name.lower() or 'ignore' in f.name.lower())
                ]
                if possible_files:
                    guess_file = possible_files[0]
                    prompt = f"Could not find '{item}', but found '{guess_file.name}'. Use it as rules? [y/n]: "
                    if terminal.prompt_confirmation(prompt):
                        _read_ignore_rules(guess_file, expanded_excludes)
                        continue
            except OSError:
                pass
            # 没找到匹配的，当作普通 Glob 处理
            expanded_excludes.append(item.replace('\\', '/'))

        # 场景 C: 普通 Glob 字符串
        else:
            expanded_excludes.append(item.replace('\\', '/').strip())
                
    return expanded_excludes