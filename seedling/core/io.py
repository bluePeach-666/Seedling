import sys
import platform
import re
from pathlib import Path, PureWindowsPath
from .logger import logger

def is_safe_path(path: Path, base_dir: Path) -> bool:
    """跨平台的路径安全边界检查"""
    try:
        p_resolved = Path(path).resolve()
        base_resolved = Path(base_dir).resolve()
        if sys.version_info >= (3, 9):
            return p_resolved.is_relative_to(base_resolved)
        else:
            try:
                p_resolved.relative_to(base_resolved)
                return True
            except ValueError:
                return False
    except Exception:
        return False

def get_dynamic_fence(content: str) -> str:
    """计算包裹内容所需的最小反引号数量"""
    max_ticks = 2
    for line in content.split('\n'):
        stripped = line.strip()
        if stripped.startswith('`'):
            ticks = len(stripped) - len(stripped.lstrip('`'))
            if ticks > max_ticks:
                max_ticks = ticks
    return '`' * (max_ticks + 1)

def extract_tree_block(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8') as f: 
            lines = f.readlines()
    except Exception as e:
        logger.error(f"ERROR reading file: {e}")
        return []

    tree_lines = []
    in_tree = False
    for i, line in enumerate(lines):
        stripped = line.rstrip()
        if not stripped:
            if in_tree: break
            continue
            
        has_tree_chars = any(c in line for c in ['├──', '└──', '│'])
        next_has_tree_chars = False
        if i + 1 < len(lines):
            next_has_tree_chars = any(c in lines[i+1] for c in ['├──', '└──', '│'])
            
        if has_tree_chars or (not in_tree and next_has_tree_chars):
            in_tree = True
            if not stripped.startswith('```'): tree_lines.append(stripped)
        elif in_tree:
            if stripped.startswith('```') or not has_tree_chars: break
                
    return tree_lines

def extract_file_contents(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8') as f: 
            lines = f.readlines()
    except Exception:
        return {}
        
    file_contents = {}
    current_file = None
    in_code_block = False
    current_content = []
    current_fence = None  
    
    for line in lines:
        if not in_code_block and line.startswith('### FILE: '):
            raw_path = line.replace('### FILE: ', '').strip()
            current_file = PureWindowsPath(raw_path).as_posix()
            current_content = []
            in_code_block = False
            current_fence = None
            continue
            
        if current_file:
            stripped_line = line.strip()
            
            if stripped_line.startswith('```') and not in_code_block:
                in_code_block = True
                match = re.match(r'^`+', stripped_line)
                current_fence = match.group() if match else '```'
                continue
                
            elif in_code_block and stripped_line == current_fence:
                in_code_block = False
                file_contents[current_file] = "".join(current_content)
                current_file = None
                current_fence = None
                continue
                
            if in_code_block:
                current_content.append(line)
                
    return file_contents

def handle_path_error(path_str):
    path = Path(path_str).resolve()
    logger.error(f"The path '{path_str}' is not a valid directory.")
    if path.is_file():
        logger.info(f"📄 It looks like this is a FILE, but I need a FOLDER.")
        logger.info(f"👉 Did you mean the parent folder: {path.parent} ?")
    elif not path.exists():
        logger.info(f"🔍 The directory does not exist. Please check the path.")
    sys.exit(1)

def clean_text_for_image(text):
    cleaned = text.replace('📁 ', '').replace('📄 ', '')
    cleaned = cleaned.replace('📁', '').replace('📄', '')
    return cleaned

def get_best_font(font_size=18):
    """Get best available font with enhanced Linux and CJK support."""
    try:
        from PIL import ImageFont # type: ignore
    except ImportError:
        logger.error("Pillow library is missing. Image export disabled.")
        return None

    system = platform.system()

    # Expanded font paths with priority order (CJK-capable fonts first)
    font_paths = {
        "Darwin": [
            # CJK primary fonts
            "/System/Library/Fonts/PingFang.ttc",
            "/System/Library/Fonts/Cache/PingFang.ttc",
            "/System/Library/Fonts/STHeiti Light.cjk",
            "/System/Library/Fonts/Hiragino Sans GB.ttc",
            # Fallback Unicode fonts
            "Arial Unicode.ttf",
            "/Library/Fonts/Arial Unicode.ttf",
            # Monospace fallback
            "Menlo.ttc",
            "/System/Library/Fonts/Menlo.ttc",
        ],
        "Windows": [
            # CJK fonts (Microsoft YaHei, SimHei, SimSun)
            "C:\\Windows\\Fonts\\msyh.ttc",      # Microsoft YaHei (recommended)
            "C:\\Windows\\Fonts\\msyhbd.ttc",    # Microsoft YaHei Bold
            "C:\\Windows\\Fonts\\simhei.ttf",    # SimHei
            "C:\\Windows\\Fonts\\simsun.ttc",    # SimSun
            "C:\\Windows\\Fonts\\simkai.ttf",    # KaiTi
            # Unicode fallback
            "C:\\Windows\\Fonts\\consola.ttf",   # Consolas
            "C:\\Windows\\Fonts\\arial.ttf",     # Arial
        ],
        "Linux": [
            # Noto CJK fonts (most common on modern distros)
            "/usr/share/fonts/noto-cjk/NotoSansCJK-Regular.ttc",
            "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
            "/usr/share/fonts/noto/NotoSansCJK-Regular.ttc",
            "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
            # WenQuanYi fonts (popular Chinese fonts)
            "/usr/share/fonts/wenquanyi/wqy-microhei/wqy-microhei.ttc",
            "/usr/share/fonts/wqy-microhei/wqy-microhei.ttc",
            "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc",
            "/usr/share/fonts/wenquanyi/wqy-zenhei/wqy-zenhei.ttc",
            # Source Han fonts (Adobe)
            "/usr/share/fonts/adobe-source-han-sans/SourceHanSansCN-Regular.otf",
            "/usr/share/fonts/opentype/source-han-sans/SourceHanSansCN-Regular.otf",
            "/usr/share/fonts/source-han-sans/SourceHanSansCN-Regular.otf",
            # Droid/Samsung CJK
            "/usr/share/fonts/truetype/droid/DroidSansFallbackFull.ttf",
            "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
            # DejaVu (fallback for Latin only)
            "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        ]
    }

    # Try hardcoded paths first
    for font_path in font_paths.get(system, []):
        try:
            return ImageFont.truetype(font_path, font_size)
        except IOError:
            continue

    # NEW: Try fontconfig dynamic discovery (Linux only)
    if system == "Linux":
        font = _try_fontconfig_discovery(font_size)
        if font:
            return font

    logger.warning("No system fonts found. Falling back to Pillow default (Limited CJK support).")
    return ImageFont.load_default()


def _try_fontconfig_discovery(font_size: int):
    """
    Use fontconfig to dynamically discover CJK fonts on Linux.
    This provides better support for headless servers and custom distros.
    """
    try:
        import subprocess

        # Query fontconfig for CJK-capable fonts (Chinese, Japanese, Korean)
        result = subprocess.run(
            ['fc-list', ':lang=zh', 'file'],
            capture_output=True,
            text=True,
            timeout=5
        )

        if result.returncode == 0 and result.stdout.strip():
            # Get first available CJK font
            for line in result.stdout.strip().split('\n')[:10]:
                font_path = line.split(':')[0].strip()
                if font_path:
                    try:
                        from PIL import ImageFont # type: ignore
                        return ImageFont.truetype(font_path, font_size)
                    except IOError:
                        continue

        # Fallback: Try to find any monospace or sans font with good Unicode coverage
        result = subprocess.run(
            ['fc-list', ':spacing=100', 'file'],  # Monospace fonts
            capture_output=True,
            text=True,
            timeout=5
        )

        if result.returncode == 0 and result.stdout.strip():
            for line in result.stdout.strip().split('\n')[:5]:
                font_path = line.split(':')[0].strip()
                if font_path:
                    try:
                        from PIL import ImageFont # type: ignore
                        return ImageFont.truetype(font_path, font_size)
                    except IOError:
                        continue

    except (subprocess.TimeoutExpired, FileNotFoundError, ImportError):
        pass

    return None

def create_image_from_text(text, output_file, line_count):
    if line_count > 1500:
        logger.error(f"❌ Directory too large ({line_count} lines). Image export aborted to prevent memory overflow.")
        logger.info("💡 Tip: Try using '--depth' to limit the scan, or export to Markdown/TXT instead.")
        return False

    try:
        from PIL import Image, ImageDraw, ImageFont # type: ignore
    except ImportError:
        logger.error("Exporting as image requires the Pillow library. Try: pip install Pillow")
        return False
    
    clean_text = clean_text_for_image(text)
    font_size = 18
    font = get_best_font(font_size)
    if font is None:
        return False

    lines = clean_text.split('\n')
    dummy_img = Image.new('RGB', (1, 1))
    draw = ImageDraw.Draw(dummy_img)
    
    max_width = 0
    line_heights = []
    
    for line in lines:
        try:
            bbox = draw.textbbox((0, 0), line, font=font)
            width = bbox[2] - bbox[0]
            height = bbox[3] - bbox[1]
        except AttributeError:
            width, height = draw.textsize(line, font=font)
            
        max_width = max(max_width, width)
        line_heights.append(max(height, font_size) + 6) 
        
    img_width = int(max_width + 80)  
    img_height = int(sum(line_heights) + 80) 
    
    bg_color = (40, 44, 52)
    text_color = (171, 178, 191)
    
    image = Image.new('RGB', (img_width, img_height), color=bg_color)
    draw = ImageDraw.Draw(image)
    
    y_offset = 40
    total_lines = len(lines)
    
    for i, line in enumerate(lines):
        draw.text((40, y_offset), line, font=font, fill=text_color)
        y_offset += line_heights[i]
        
        if i % max(1, (total_lines // 20)) == 0 or i == total_lines - 1:
            percent = int((i + 1) / total_lines * 100)
            bar = '█' * (percent // 5) + '-' * (20 - (percent // 5))
            sys.stdout.write(f"\r🎨 Rendering Image: [{bar}] {percent}% ")
            sys.stdout.flush()
            
    print() 
    try:
        image.save(output_file)
        return True
    except Exception as e:
        logger.error(f"Failed to save image: {e}")
        return False