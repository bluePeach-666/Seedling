from __future__ import annotations
import sys
import logging
from abc import ABC, abstractmethod
from typing import Final, Optional, Any
from .exceptions import ConfigurationError

class AbstractLogger(ABC):
    """
    Seedling-tools 日志系统的抽象基类接口。
    定义了日志记录器的标准行为，便于后续可能的扩展或替换实现。
    """
    
    @abstractmethod
    def configure(self, verbose: bool = False, quiet: bool = False) -> None:
        """配置日志级别与处理器"""
        pass

    @abstractmethod
    def info(self, msg: str) -> None:
        """记录常规信息日志"""
        pass

    @abstractmethod
    def debug(self, msg: str) -> None:
        """记录调试信息日志"""
        pass

    @abstractmethod
    def warning(self, msg: str) -> None:
        """记录警告信息日志"""
        pass

    @abstractmethod
    def error(self, msg: str) -> None:
        """记录错误信息日志"""
        pass


class _SeedlingCLIFormatter(logging.Formatter):
    """命令行输出定制日志格式化器"""
    
    def format(self, record: logging.LogRecord) -> str:
        """根据不同的日志级别应用对应的终端前缀格式"""
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


class SeedlingToolsLogger(AbstractLogger):
    """全局唯一日志记录器单例实现类"""
    
    _instance: Optional[SeedlingToolsLogger] = None
    _logger: Optional[logging.Logger] = None

    def __new__(cls: Any) -> SeedlingToolsLogger:
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._logger = logging.getLogger("seedling_tools")
            cls._instance._logger.propagate = False
        return cls._instance

    def configure(self, verbose: bool = False, quiet: bool = False) -> None:
        """
        初始化并配置全局日志等级和流处理器。
        Args:
            verbose: 是否开启 DEBUG 级别日志。
            quiet: 是否仅输出 ERROR 级别日志。  
        Raises:
            ConfigurationError: 底层日志实例缺失或流处理器装载失败时抛出。
        """
        if self._logger is None:
            raise ConfigurationError(
                message="Underlying logger instance is not initialized.",
                hint="Ensure the singleton was instantiated correctly."
            )

        level: int = logging.INFO
        
        if verbose: 
            level = logging.DEBUG
        elif quiet: 
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
        if self._logger:
            self._logger.info(msg)

    def debug(self, msg: str) -> None:
        if self._logger:
            self._logger.debug(msg)

    def warning(self, msg: str) -> None:
        if self._logger:
            self._logger.warning(msg)

    def error(self, msg: str) -> None:
        if self._logger:
            self._logger.error(msg)

logger: Final[AbstractLogger] = SeedlingToolsLogger()
"""全局共享的日志实例单例"""