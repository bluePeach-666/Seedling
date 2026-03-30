from __future__ import annotations
import sys
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Final

from .log_helper import logger
from .patterns import SingletonMeta

@dataclass(frozen=True)
class TerminalTheme:
    dir_icon: str = "[DIR]"
    file_icon: str = "[FILE]"
    match_icon: str = "[MATCHED]"
    wait_icon: str = "..."
    success_icon: str = "SUCCESS"

class AbstractTerminal(ABC):
    @abstractmethod
    def configure_environment(self, no_color: bool = False) -> None:
        pass

    @abstractmethod
    def prompt_confirmation(self, prompt_text: str, default_no: bool = True) -> bool:
        pass

    @abstractmethod
    def render_progress(self, current: int, label: str = "Processing", quiet: bool = False) -> None:
        pass

    @abstractmethod
    def display_banner(self) -> None:
        pass

class SeedlingTerminal(AbstractTerminal, metaclass=SingletonMeta):
    def __init__(self) -> None:
        self._theme: Final[TerminalTheme] = TerminalTheme()

    def configure_environment(self, no_color: bool = False) -> None:
        if sys.platform == "win32":
            self._ensure_windows_utf8()

    def _ensure_windows_utf8(self) -> None:
        stream_names: Final[tuple[str, str]] = ('stdout', 'stderr')
        for stream_name in stream_names:
            try:
                stream = getattr(sys, stream_name)
                if stream is not None:
                    if hasattr(stream, 'reconfigure'):
                        stream.reconfigure(encoding='utf-8', line_buffering=True)
            except ValueError as err:
                logger.warning(f"Terminal encoding fallback for {stream_name} bypassed: {err}")
            except TypeError as err:
                logger.warning(f"Terminal encoding fallback for {stream_name} bypassed: {err}")
            except OSError as err:
                logger.warning(f"Terminal encoding fallback for {stream_name} bypassed: {err}")
            except AttributeError as err:
                logger.warning(f"Terminal encoding fallback for {stream_name} bypassed: {err}")

    def prompt_confirmation(self, prompt_text: str, default_no: bool = True) -> bool:
        if sys.stdin.isatty() is False:
            safe_choice: str
            if default_no is True:
                safe_choice = "NO"
            else:
                safe_choice = "YES"
                
            logger.warning(f"Non-interactive terminal. Auto-answering {safe_choice} to: {prompt_text}")
            
            if default_no is True:
                return False
            else:
                return True

        while True:
            try:
                raw_input: str = input(prompt_text)
                ans: str = raw_input.strip().lower()
                
                if ans == 'y':
                    return True
                elif ans == 'yes':
                    return True
                elif ans == 'n':
                    return False
                elif ans == 'no':
                    return False
                else:
                    print("Invalid input. Please enter 'y' or 'n'.")
                    
            except EOFError:
                logger.warning("Input stream closed (EOF).")
                if default_no is True:
                    return False
                else:
                    return True

    def render_progress(self, current: int, label: str = "Processing", quiet: bool = False) -> None:
        if quiet is True:
            return
            
        if sys.stdout.isatty() is False:
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