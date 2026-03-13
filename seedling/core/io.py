import sys
import platform
from pathlib import Path

def extract_tree_block(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8') as f: lines = f.readlines()
    except Exception as e:
        sys.stderr.write(f"\n❌ ERROR reading file: {e}\n")
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
        with open(file_path, 'r', encoding='utf-8') as f: lines = f.readlines()
    except Exception:
        return {}
        
    file_contents = {}
    current_file = None
    in_code_block = False
    current_content = []
    
    for line in lines:
        if line.startswith('### FILE: '):
            current_file = line.replace('### FILE: ', '').strip().replace('\\', '/')
            current_content = []
            in_code_block = False
            continue
            
        if current_file:
            if line.startswith('```') and not in_code_block:
                in_code_block = True
                continue
            elif line.startswith('```') and in_code_block:
                in_code_block = False
                file_contents[current_file] = "".join(current_content)
                current_file = None
                continue
                
            if in_code_block:
                current_content.append(line)
                
    return file_contents

def handle_path_error(path_str):
    path = Path(path_str).resolve()
    print(f"\n❌ ERROR: The path '{path_str}' is not a valid directory.")
    if path.is_file():
        print(f"📄 It looks like this is a FILE, but I need a FOLDER.")
        print(f"👉 Did you mean the parent folder: {path.parent} ?")
    elif not path.exists():
        print(f"🔍 The directory does not exist. Please check the path.")
    sys.exit(1)

def clean_text_for_image(text):
    cleaned = text.replace('📁 ', '').replace('📄 ', '')
    cleaned = cleaned.replace('📁', '').replace('📄', '')
    return cleaned

def get_best_font(font_size=18):
    try:
        from PIL import ImageFont # type: ignore
    except ImportError:
        return None

    system = platform.system()
    if system == "Darwin":
        font_paths = ["PingFang.ttc", "Hiragino Sans GB.ttc", "Arial Unicode.ttf", "Menlo.ttc"]
    elif system == "Windows":
        font_paths = ["msyh.ttc", "simhei.ttf", "simsun.ttc", "consola.ttf"]
    else:
        font_paths = ["NotoSansCJK-Regular.ttc", "wqy-microhei.ttc", "DejaVuSansMono.ttf"]
        
    for font_name in font_paths:
        try:
            return ImageFont.truetype(font_name, font_size)
        except IOError:
            continue
    return ImageFont.load_default()

def create_image_from_text(text, output_file, line_count):
    if line_count > 1500:
        print(f"\n⚠️ WARNING: Directory too large ({line_count} lines). Generating an image may cause memory overflow.")
        return False

    try:
        from PIL import Image, ImageDraw, ImageFont # type: ignore
    except ImportError:
        print("\n❌ ERROR: Exporting as image requires the Pillow library (pip install Pillow).")
        return False
    
    clean_text = clean_text_for_image(text)
    font_size = 18
    font = get_best_font(font_size)
    if font is None:
        font = ImageFont.load_default()

    lines = clean_text.split('\n')
    dummy_img = Image.new('RGB', (1, 1))
    draw = ImageDraw.Draw(dummy_img)
    
    max_width, total_height = 0, 0
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
        print(f"\n❌ ERROR saving image: {e}")
        return False