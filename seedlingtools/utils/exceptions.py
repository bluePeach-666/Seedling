from __future__ import annotations
from typing import Final, Optional, Any

class SeedlingToolsError(Exception):
    """
    Seedling-tools 异常基类。
    Attributes:
        message: 开发者/用户可见的错误描述。
        exit_code: 进程退出状态码。
        hint: 给用户的操作建议。
        context: 包含额外调试信息的字典。
    """
    def __init__(
        self, 
        message: str, 
        exit_code: int = 1, 
        hint: Optional[str] = None,
        context: Optional[dict[str, Any]] = None
    ) -> None:
        super().__init__(message)
        self.message: Final[str] = message
        self.exit_code: Final[int] = exit_code
        self.hint: Final[Optional[str]] = hint
        self.context: Final[dict[str, Any]] = context or {}

    def __str__(self) -> str:
        """格式化输出"""
        base: str = f"[{self.__class__.__name__}] {self.message}"
        if self.hint:
            base += f"\n💡 HINT: {self.hint}"
        return base

class SystemProbeError(SeedlingToolsError):
    """系统环境探测失败时抛出"""
    def __init__(
        self, 
        message: str, 
        hint: Optional[str] = "Check system permissions or resource limits.",
        **kwargs: Any
    ) -> None:
        # 默认退出码 70
        super().__init__(message, exit_code=70, hint=hint, **kwargs)

class FileSystemError(SeedlingToolsError):
    """处理文件读写、权限或路径安全校验异常"""
    def __init__(
        self, 
        message: str, 
        hint: Optional[str] = "Ensure the target path is readable and within project boundaries.",
        **kwargs: Any
    ) -> None:
        # 默认退出码 74 
        super().__init__(message, exit_code=74, hint=hint, **kwargs)

class ConfigurationError(SeedlingToolsError):
    """配置项缺失或格式错误"""
    def __init__(
        self, 
        message: str, 
        hint: Optional[str] = "Verify the CLI arguments or config file syntax.",
        **kwargs: Any
    ) -> None:
        # 默认退出码 64 
        super().__init__(message, exit_code=64, hint=hint, **kwargs)