"""
Unified exception hierarchy for Seedling-tools.
"""

from __future__ import annotations
from typing import Final, Optional, Dict, Any

class SeedlingToolsError(Exception):
    def __init__(
        self, 
        message: str, 
        exit_code: int = 1, 
        hint: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> None:
        super().__init__(message)
        self.message: Final[str] = message
        self.exit_code: Final[int] = exit_code
        self.hint: Final[Optional[str]] = hint
        
        resolved_context: Dict[str, Any]
        if context is not None:
            resolved_context = context
        else:
            resolved_context = {}
            
        self.context: Final[Dict[str, Any]] = resolved_context

    def __str__(self) -> str:
        base_message: str = f"[{self.__class__.__name__}] {self.message}"
        
        if self.hint is not None:
            base_message = f"{base_message}\nHINT: {self.hint}"
            
        return base_message

class SystemProbeError(SeedlingToolsError):
    def __init__(
        self, 
        message: str, 
        hint: Optional[str] = "Check system permissions or resource limits.",
        **kwargs: Any
    ) -> None:
        super().__init__(message, exit_code=70, hint=hint, **kwargs)

class FileSystemError(SeedlingToolsError):
    def __init__(
        self, 
        message: str, 
        hint: Optional[str] = "Ensure the target path is readable and within project boundaries.",
        **kwargs: Any
    ) -> None:
        super().__init__(message, exit_code=74, hint=hint, **kwargs)

class ConfigurationError(SeedlingToolsError):
    def __init__(
        self,
        message: str,
        hint: Optional[str] = "Verify the CLI arguments or config file syntax.",
        **kwargs: Any
    ) -> None:
        super().__init__(message, exit_code=64, hint=hint, **kwargs)

class ConfigurationLoadError(ConfigurationError):
    def __init__(
        self,
        message: str,
        hint: Optional[str] = "Check that the configuration path exists and is readable.",
        **kwargs: Any
    ) -> None:
        super().__init__(message=message, hint=hint, **kwargs)

class ConfigurationCorruptionError(ConfigurationError):
    def __init__(
        self,
        message: str,
        hint: Optional[str] = "Fix or remove the malformed Seedling configuration file.",
        **kwargs: Any
    ) -> None:
        super().__init__(message=message, hint=hint, **kwargs)

class ConfigurationWriteError(ConfigurationError):
    def __init__(
        self,
        message: str,
        hint: Optional[str] = "Check permissions for the Seedling configuration directory.",
        **kwargs: Any
    ) -> None:
        super().__init__(message=message, hint=hint, **kwargs)

class PluginLoadError(SeedlingToolsError):
    def __init__(
        self,
        message: str,
        hint: Optional[str] = "Check the custom command plugin implementation.",
        **kwargs: Any
    ) -> None:
        super().__init__(message, exit_code=65, hint=hint, **kwargs)