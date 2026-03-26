from pathlib import Path
from .logger import logger
from .config import TEXT_EXTENSIONS, SPECIAL_TEXT_NAMES

def is_text_file(file_path: Path) -> bool:
    """基础检测"""
    if file_path.suffix.lower() in TEXT_EXTENSIONS: # 常规扩展名
        return True
    if file_path.name.lower() in SPECIAL_TEXT_NAMES: #  特殊无后缀配置文件 
        return True     
    if file_path.name.startswith('.') and not file_path.suffix: # 隐藏配置文件
        return True       
    return False

def is_binary_content(file_path: Path) -> bool:
    """字节探测"""
    try:
        # 二进制只读
        with open(file_path, 'rb') as f:
            chunk = f.read(1024)
            # 常见二进制头部特征
            binary_signatures = [
                b'\x89PNG', b'GIF89a', b'GIF87a', b'\xff\xd8\xff',
                b'MZ', b'\x7fELF', b'PK\x03\x04', b'%PDF-', b'Rar!\x1a\x07'
            ]
            # 拦截
            if b'\x00' in chunk or any(chunk.startswith(sig) for sig in binary_signatures):
                return True
                
    except Exception as e: # 跳过
        logger.debug(f"Binary probe failed for {file_path.name}: {e}")
        return True
    return False
