from __future__ import annotations
import sys
import logging
from abc import ABC, abstractmethod
from typing import Final, Any

from .exceptions import ConfigurationError
from .patterns import SingletonMeta

class AbstractLogger(ABC):
    @abstractmethod
    def configure(self, verbose: bool = False, quiet: bool = False) -> None:
        pass

    @abstractmethod
    def info(self, msg: str) -> None:
        pass

    @abstractmethod
    def debug(self, msg: str) -> None:
        pass

    @abstractmethod
    def warning(self, msg: str) -> None:
        pass

    @abstractmethod
    def error(self, msg: str) -> None:
        pass


class _SeedlingCLIFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        if record.levelno == logging.INFO:
            self._style._fmt = "%(message)s"
        elif record.levelno == logging.DEBUG:
            self._style._fmt = "[DEBUG] %(message)s"
        elif record.levelno == logging.WARNING:
            self._style._fmt = "[WARNING] %(message)s"
        elif record.levelno == logging.ERROR:
            self._style._fmt = "[ERROR] %(message)s"
        elif record.levelno == logging.CRITICAL:
            self._style._fmt = "[FATAL] %(message)s"
        else:
            self._style._fmt = "[LOG] %(message)s"
            
        return super().format(record)


class SeedlingToolsLogger(AbstractLogger, metaclass=SingletonMeta):
    def __init__(self) -> None:
        self._logger: logging.Logger = logging.getLogger("seedling_tools")
        self._logger.propagate = False

    def configure(self, verbose: bool = False, quiet: bool = False) -> None:
        if self._logger is None:
            raise ConfigurationError(
                message="Underlying logger instance is not initialized.",
                hint="Ensure the singleton was instantiated correctly."
            )

        level: int = logging.INFO
        
        if verbose is True:
            level = logging.DEBUG
        elif quiet is True:
            level = logging.ERROR
            
        if self._logger.hasHandlers():
            self._logger.handlers.clear()
            
        try:
            handler: logging.StreamHandler[Any] = logging.StreamHandler(sys.stdout)
            handler.setFormatter(_SeedlingCLIFormatter())
            
            self._logger.setLevel(level)
            self._logger.addHandler(handler)
        except OSError as err:
            raise ConfigurationError(
                message=f"Failed to configure logger stream handlers: {err}",
                hint="Check system standard output stream availability.",
                context={"error": str(err)}
            ) from err

    def info(self, msg: str) -> None:
        if self._logger is not None:
            self._logger.info(msg)

    def debug(self, msg: str) -> None:
        if self._logger is not None:
            self._logger.debug(msg)

    def warning(self, msg: str) -> None:
        if self._logger is not None:
            self._logger.warning(msg)

    def error(self, msg: str) -> None:
        if self._logger is not None:
            self._logger.error(msg)

logger: Final[AbstractLogger] = SeedlingToolsLogger()