from __future__ import annotations
import platform
import sys
import subprocess
from typing import Final
from pathlib import Path
from importlib.metadata import version, PackageNotFoundError
from .exceptions import SystemProbeError
    
# 系统资源探测相关的内部常量
_MEM_FALLBACK_MB: Final[int] = 512
_MEM_MIN_LIMIT_MB: Final[int] = 32
_MEM_RESERVE_RATIO: Final[float] = 0.10
_RECURSION_BUFFER: Final[int] = 100
_RECURSION_FLOOR: Final[int] = 100
_PROBE_TIMEOUT: Final[int] = 5
_KB_FACTOR: Final[int] = 1024
_MB_FACTOR: Final[int] = 1024 * 1024

def is_relative_to_compat(path: Path, base: Path) -> bool:
    """判断 path 是否为 base 的子路径，兼容 Python 3.8"""
    if sys.version_info >= (3, 9):
        return path.is_relative_to(base)
    
    try:
        path.relative_to(base)
        return True
    except ValueError:
        return False

def get_package_version() -> str:
    """获取包的安装版本"""
    try:
        return version("Seedling-tools")
    except (PackageNotFoundError, ImportError):
        return "dev"

def get_recursion_limit() -> int:
    """计算安全的递归深度上限"""
    try:
        limit: int = sys.getrecursionlimit() - _RECURSION_BUFFER
        return max(limit, _RECURSION_FLOOR)
    except Exception as err:
        raise SystemProbeError(
            message="Critical failure accessing system recursion limit",
            hint="Check Python interpreter security constraints.",
            context={"raw_limit": getattr(sys, "getrecursionlimit", lambda: 0)()}
        ) from err

def get_memory_limit_mb() -> int:
    """探测物理内存并计算内存保护阈值"""
    system: Final[str] = platform.system()
    total_mb: float = 0.0

    try:
        if system == "Linux":
            total_mb = _probe_linux_mem()
        elif system == "Darwin":
            total_mb = _probe_macos_mem()
        elif system == "Windows":
            total_mb = _probe_windows_mem()
    except (OSError, ValueError, subprocess.SubprocessError) as err:
        raise SystemProbeError(
            message=f"Hardware probe failed on platform: {system}",
            hint="The environment might lack necessary system-level access permissions.",
            context={"platform": system}
        ) from err

    if total_mb <= 0:
        return _MEM_FALLBACK_MB

    suggested_limit = int(total_mb * _MEM_RESERVE_RATIO)
    return max(suggested_limit, _MEM_MIN_LIMIT_MB)

# 内部函数
def _probe_linux_mem() -> float:
    with open('/proc/meminfo', 'r', encoding='utf-8') as f:
        for line in f:
            if 'MemTotal' in line:
                return int(line.split()[1]) / _KB_FACTOR
    return 0.0
def _probe_macos_mem() -> float:
    out = subprocess.check_output(
        ['sysctl', '-n', 'hw.memsize'], 
        timeout=_PROBE_TIMEOUT
    )
    return int(out.decode('utf-8').strip()) / _MB_FACTOR
def _probe_windows_mem() -> float:
    import ctypes
    from ctypes import wintypes

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
    
    windll = getattr(ctypes, "windll", None)
    if windll and windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(stat)):
        return stat.ullTotalPhys / _MB_FACTOR
    
    return 0.0