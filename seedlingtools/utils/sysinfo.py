from __future__ import annotations
import platform
import sys
import subprocess
from typing import Final, Any
from pathlib import Path
from importlib.metadata import version, PackageNotFoundError
from .exceptions import SystemProbeError
    
_MEM_FALLBACK_MB: Final[int] = 512
_MEM_MIN_LIMIT_MB: Final[int] = 32
_MEM_RESERVE_RATIO: Final[float] = 0.10
_RECURSION_BUFFER: Final[int] = 100
_RECURSION_FLOOR: Final[int] = 100
_PROBE_TIMEOUT: Final[int] = 5
_KB_FACTOR: Final[int] = 1024
_MB_FACTOR: Final[int] = 1024 * 1024

def is_relative_to_compat(path: Path, base: Path) -> bool:
    if sys.version_info >= (3, 9):
        return path.is_relative_to(base)
    else:
        try:
            path.relative_to(base)
            return True
        except ValueError:
            return False

def get_package_version() -> str:
    try:
        return version("Seedling-tools")
    except PackageNotFoundError:
        return "dev"
    except ImportError:
        return "dev"

def get_recursion_limit() -> int:
    try:
        limit: int = sys.getrecursionlimit() - _RECURSION_BUFFER
        if limit > _RECURSION_FLOOR:
            return limit
        else:
            return _RECURSION_FLOOR
    except Exception as err:
        raise SystemProbeError(
            message="Critical failure accessing system recursion limit",
            hint="Check Python interpreter security constraints.",
            context={"raw_limit": getattr(sys, "getrecursionlimit", lambda: 0)()}
        ) from err

def get_memory_limit_mb() -> int:
    system: Final[str] = platform.system()
    total_mb: float = 0.0

    try:
        if system == "Linux":
            total_mb = _probe_linux_mem()
        elif system == "Darwin":
            total_mb = _probe_macos_mem()
        elif system == "Windows":
            total_mb = _probe_windows_mem()
        else:
            total_mb = 0.0
    except OSError as err:
        raise SystemProbeError(
            message=f"Hardware probe failed on platform: {system}",
            context={"platform": system}
        ) from err
    except ValueError as err:
        raise SystemProbeError(
            message=f"Value parsing failed on platform: {system}",
            context={"platform": system}
        ) from err
    except subprocess.SubprocessError as err:
        raise SystemProbeError(
            message=f"Subprocess execution failed on platform: {system}",
            context={"platform": system}
        ) from err

    if total_mb <= 0:
        return _MEM_FALLBACK_MB

    suggested_limit: int = int(total_mb * _MEM_RESERVE_RATIO)
    if suggested_limit > _MEM_MIN_LIMIT_MB:
        return suggested_limit
    else:
        return _MEM_MIN_LIMIT_MB

def _probe_linux_mem() -> float:
    try:
        with open('/proc/meminfo', 'r', encoding='utf-8') as f:
            for line in f:
                if 'MemTotal' in line:
                    parts: list[str] = line.split()
                    kb_value: int = int(parts[1])
                    return kb_value / _KB_FACTOR
    except OSError:
        pass
    return 0.0

def _probe_macos_mem() -> float:
    try:
        out: bytes = subprocess.check_output(
            ['sysctl', '-n', 'hw.memsize'], 
            timeout=_PROBE_TIMEOUT
        )
        raw_str: str = out.decode('utf-8').strip()
        mem_bytes: int = int(raw_str)
        return mem_bytes / _MB_FACTOR
    except (subprocess.SubprocessError, ValueError, OSError):
        return 0.0

def _probe_windows_mem() -> float:
    try:
        import ctypes
        from ctypes import wintypes
    except ImportError:
        return 0.0

    class MEMORYSTATUSEX(ctypes.Structure):
        _fields_ = [
            ("dwLength", wintypes.DWORD),
            ("dwMemoryLoad", wintypes.DWORD),
            ("ullTotalPhys", ctypes.c_uint64),
            ("ullAvailPhys", ctypes.c_uint64),
            ("ullTotalPageFile", ctypes.c_uint64),
            ("ullAvailPageFile", ctypes.c_uint64),
            ("ullTotalVirtual", ctypes.c_uint64),
            ("ullAvailVirtual", ctypes.c_uint64),
            ("sullAvailExtendedVirtual", ctypes.c_uint64),
        ]

    stat = MEMORYSTATUSEX()
    stat.dwLength = ctypes.sizeof(MEMORYSTATUSEX)
    
    windll: Any = getattr(ctypes, "windll", None)
    if windll is not None:
        if windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(stat)):
            return stat.ullTotalPhys / _MB_FACTOR
            
    return 0.0