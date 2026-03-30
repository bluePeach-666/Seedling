from __future__ import annotations
from typing import Any, Dict
import abc

class SingletonMeta(abc.ABCMeta):
    _instances: Dict[type, Any] = {}

    def __call__(cls, *args: Any, **kwargs: Any) -> Any:
        if cls not in cls._instances:
            cls._instances[cls] = super(SingletonMeta, cls).__call__(*args, **kwargs)
        
        return cls._instances[cls]