from __future__ import annotations
import sys
import os
import io
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Final, Optional
from .log_helper import logger
from .exceptions import FileSystemError

@dataclass(frozen=True)
class TerminalTheme:
    """终端 UI 主题配置数据结构"""
    dir_icon: str = "[DIR]"
    file_icon: str = "[FILE]"
    match_icon: str = "[MATCHED]"
    wait_icon: str = "..."
    success_icon: str = "SUCCESS"


class AbstractTerminal(ABC):
    """终端交互界面的抽象基类"""
    
    @abstractmethod
    def configure_environment(self, no_color: bool = False) -> None:
        """配置终端环境与编码"""
        pass

    @abstractmethod
    def prompt_confirmation(self, prompt_text: str, default_no: bool = True) -> bool:
        """提供安全的交互式确认提示"""
        pass

    @abstractmethod
    def render_progress(self, current: int, label: str = "Processing", quiet: bool = False) -> None:
        """渲染非阻塞的进度指示器"""
        pass

    @abstractmethod
    def display_banner(self) -> None:
        """显示工具标语"""
        pass


class SeedlingTerminal(AbstractTerminal):
    """终端交互标准实现类，采用单例模式管控标准输入输出流"""
    
    _instance: Optional[SeedlingTerminal] = None
    _theme: TerminalTheme

    def __new__(cls) -> SeedlingTerminal:
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._theme = TerminalTheme()
        return cls._instance

    def configure_environment(self, no_color: bool = False) -> None:
        if sys.platform == "win32":
            self._ensure_windows_utf8()

    def _ensure_windows_utf8(self) -> None:
        for stream_name in ('stdout', 'stderr'):
            try:
                stream = getattr(sys, stream_name)
                if stream and hasattr(stream, 'reconfigure'):
                    stream.reconfigure(encoding='utf-8', line_buffering=True)
            except (ValueError, TypeError, OSError, AttributeError) as err:
                logger.warning(f"Terminal encoding fallback for {stream_name} bypassed: {err}")

    def prompt_confirmation(self, prompt_text: str, default_no: bool = True) -> bool:
        if not sys.stdin.isatty():
            safe_choice = "NO" if default_no else "YES"
            logger.warning(f"Non-interactive terminal. Auto-answering {safe_choice} to: {prompt_text}")
            return not default_no

        while True:
            try:
                ans: str = input(prompt_text).strip().lower()
                if ans in ('y', 'yes'):
                    return True
                if ans in ('n', 'no'):
                    return False
                print("Invalid input. Please enter 'y' or 'n'.")
            except EOFError:
                logger.warning("Input stream closed (EOF).")
                return not default_no

    def render_progress(self, current: int, label: str = "Processing", quiet: bool = False) -> None:
        if quiet or not sys.stdout.isatty():
            return
            
        pulse: Final[tuple[str, ...]] = ("#---", "-#--", "--#-", "---#", "--#-", "-#--")
        idx: int = (current // 5) % len(pulse)
        sys.stdout.write(f"\r{self._theme.wait_icon} {label}... [{pulse[idx]}] Scanned: {current} items ")
        sys.stdout.flush()

    def display_banner(self) -> None:
        banner: Final[str] = """
    ==================================================================
      Seedling-tools: Directory Tree Scanner & Builder
    ==================================================================
    [ Basic Usage ]
      scan .                  -> Scan current directory
      
    [ Advanced Features ]
      scan . --full           -> Context Aggregation for LLMs
      scan . --skeleton       -> Extract AST structure
      build blueprint.md      -> Reconstruct file system
    ==================================================================
        """
        print(banner)

terminal: Final[AbstractTerminal] = SeedlingTerminal()
"""全局终端交互单例"""