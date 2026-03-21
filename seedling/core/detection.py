"""
File type detection utilities for Seedling.
"""
from pathlib import Path
from .logger import logger
from .config import TEXT_EXTENSIONS, SPECIAL_TEXT_NAMES


def is_text_file(file_path: Path) -> bool:
    """Determine if file is a known text file type."""
    if file_path.suffix.lower() in TEXT_EXTENSIONS:
        return True
    if file_path.name.lower() in SPECIAL_TEXT_NAMES:
        return True
    if file_path.name.startswith('.') and not file_path.suffix:
        return True
    return False


def is_binary_content(file_path: Path) -> bool:
    """Heuristic binary detection with magic numbers."""
    try:
        with open(file_path, 'rb') as f:
            chunk = f.read(1024)
            # Common binary file signatures
            binary_signatures = [
                b'\x89PNG', b'GIF89a', b'GIF87a', b'\xff\xd8\xff',
                b'MZ', b'\x7fELF', b'PK\x03\x04', b'%PDF-', b'Rar!\x1a\x07'
            ]
            if b'\x00' in chunk or any(chunk.startswith(sig) for sig in binary_signatures):
                return True
    except Exception as e:
        logger.debug(f"Binary probe failed for {file_path.name}: {e}")
        return True
    return False
