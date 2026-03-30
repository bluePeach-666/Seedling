from __future__ import annotations
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Final, List, Optional, Any

from .log_helper import logger
from .exceptions import SystemProbeError, FileSystemError
from .patterns import SingletonMeta

class AbstractImageRenderer(ABC):
    @abstractmethod
    def render_text_to_image(self, text: str, output_path: Path, line_count: int) -> bool:
        pass

class PillowImageRenderer(AbstractImageRenderer, metaclass=SingletonMeta):
    def __init__(self) -> None:
        self._font_cache: Optional[Any] = None
        self._bg_color: Final[tuple[int, int, int]] = (40, 44, 52)
        self._text_color: Final[tuple[int, int, int]] = (171, 178, 191)
        self._font_size: Final[int] = 18

    def _get_system_font(self) -> Any:
        if self._font_cache is not None:
            return self._font_cache

        try:
            from PIL import ImageFont # type: ignore
        except ImportError as err:
            raise SystemProbeError(
                message="Pillow library is required for image rendering.",
                hint="Run 'pip install Pillow' to enable this feature."
            ) from err

        font_paths: Final[tuple[str, ...]] = (
            "/System/Library/Fonts/PingFang.ttc",
            "/System/Library/Fonts/STHeiti Light.cjk",
            "/System/Library/Fonts/Hiragino Sans GB.ttc",
            "C:\\Windows\\Fonts\\msyh.ttc",
            "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"
        )

        for path in font_paths:
            try:
                self._font_cache = ImageFont.truetype(path, self._font_size)
                return self._font_cache
            except OSError:
                continue

        logger.warning("System specific fonts not found. Falling back to default.")
        self._font_cache = ImageFont.load_default()
        return self._font_cache

    def render_text_to_image(self, text: str, output_path: Path, line_count: int) -> bool:
        if line_count > 1500:
            logger.error(f"Payload too large ({line_count} lines). Image export aborted to prevent memory overflow.")
            logger.info("Tip: Try using '--depth' to limit the scan, or export to Markdown/TXT instead.")
            return False

        try:
            from PIL import Image, ImageDraw # type: ignore
        except ImportError as err:
            raise SystemProbeError(message="Pillow is missing.", hint="pip install Pillow") from err
            
        font: Any = self._get_system_font()
        lines: List[str] = text.split('\n')
        
        dummy_img: Any = Image.new('RGB', (1, 1))
        draw: Any = ImageDraw.Draw(dummy_img)
        
        max_width: int = 0
        line_heights: List[int] = []
        
        for line in lines:
            width: int
            height: int
            
            try:
                bbox: tuple[int, int, int, int] = draw.textbbox((0, 0), line, font=font)
                width = bbox[2] - bbox[0]
                height = bbox[3] - bbox[1]
            except AttributeError:
                width, height = draw.textsize(line, font=font) # type: ignore
                
            if width > max_width:
                max_width = width
                
            if height > self._font_size:
                line_heights.append(height + 6)
            else:
                line_heights.append(self._font_size + 6)
                
        img_width: int = int(max_width + 80)
        img_height: int = int(sum(line_heights) + 80)
        
        image: Any = Image.new('RGB', (img_width, img_height), color=self._bg_color)
        draw = ImageDraw.Draw(image)
        
        y_offset: int = 40
        for i, line in enumerate(lines):
            draw.text((40, y_offset), line, font=font, fill=self._text_color)
            y_offset += line_heights[i]
            
        try:
            image.save(output_path)
            return True
        except OSError as err:
            raise FileSystemError(
                message=f"Failed to write image to disk: {output_path}",
                context={"path": str(output_path)}
            ) from err

image_renderer: Final[AbstractImageRenderer] = PillowImageRenderer()