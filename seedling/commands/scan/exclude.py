from pathlib import Path
from seedling.core.logger import logger
from seedling.core.ui import ask_yes_no

def _read_ignore_rules(file_path: Path, rules_list: list):
    """读取并加入过滤规则列表，预处理规则格式"""
    logger.info(f"📄 Reading exclusion rules from: {file_path.name}")
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                # 忽略空行和注释行
                if line and not line.startswith('#'):
                    # 统一为 POSIX 路径格式、移除多余空格
                    clean_rule = line.replace('\\', '/').strip()
                    rules_list.append(clean_rule)
    except Exception as e:
        logger.error(f"Failed to read {file_path}: {e}")

def expand_excludes(raw_excludes: list) -> list:
    """智能解析 exclude 参数"""
    expanded_excludes = []
    
    for item in raw_excludes:
        item_path = Path(item)
        has_ignore_keyword = 'ignore' in item.lower()

        if item_path.is_file():
            if has_ignore_keyword:
                # 明确的文件路径且带有 ignore
                _read_ignore_rules(item_path, expanded_excludes)
            else:
                # 是个文件，但名字不像过滤配置
                prompt = f"❓ File '{item}' found. Read exclusion rules from it? (Select 'n' to treat as a glob string) [y/n]: "
                if ask_yes_no(prompt):
                    _read_ignore_rules(item_path, expanded_excludes)
                else:
                    expanded_excludes.append(item)
        else:
            if has_ignore_keyword:
                # 路径不存在，但用户输入了带 ignore 的字样，尝试寻找
                possible_files = [
                    f for f in Path.cwd().iterdir() 
                    if f.is_file() and item.lower() in f.name.lower()
                ]
                if possible_files:
                    guess_file = possible_files[0] 
                    prompt = f"❓ Could not find '{item}', but found '{guess_file.name}'. Read rules from it? [y/n]: "
                    if ask_yes_no(prompt):
                        _read_ignore_rules(guess_file, expanded_excludes)
                    else:
                        expanded_excludes.append(item)
                else:
                    expanded_excludes.append(item)
            else:
                # 普通的过滤字段模式，预处理为 POSIX 格式
                clean_item = item.replace('\\', '/').strip()
                expanded_excludes.append(clean_item)
                
    return expanded_excludes