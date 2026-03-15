import platform
import sys

def get_system_mem_limit_mb():
    fallback_mb = 512
    try:
        system = platform.system()
        total_mb = 0
        
        if system == "Linux":
            with open('/proc/meminfo', 'r') as f:
                for line in f:
                    if 'MemTotal' in line:
                        total_mb = int(line.split()[1]) / 1024
                        break
        elif system == "Darwin": # macOS
            import subprocess
            out = subprocess.check_output(['sysctl', '-n', 'hw.memsize']).decode('utf-8')
            total_mb = int(out.strip()) / (1024 * 1024)
        elif system == "Windows":
            import ctypes
            class MEMORYSTATUSEX(ctypes.Structure):
                _fields_ = [
                    ("dwLength", ctypes.c_ulong),
                    ("dwMemoryLoad", ctypes.c_ulong),
                    ("ullTotalPhys", ctypes.c_ulonglong),
                    ("ullAvailPhys", ctypes.c_ulonglong),
                    ("ullTotalPageFile", ctypes.c_ulonglong),
                    ("ullAvailPageFile", ctypes.c_ulonglong),
                    ("ullTotalVirtual", ctypes.c_ulonglong),
                    ("ullAvailVirtual", ctypes.c_ulonglong),
                    ("sullAvailExtendedVirtual", ctypes.c_ulonglong),
                ]
            stat = MEMORYSTATUSEX()
            stat.dwLength = ctypes.sizeof(MEMORYSTATUSEX)
            windll = getattr(ctypes, "windll", None)
            if windll is not None:
                windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(stat))
                total_mb = stat.ullTotalPhys / (1024 * 1024)

        if total_mb > 0:
            return max(32, int(total_mb * 0.10))
            
    except Exception:
        pass
        
    return fallback_mb

def get_system_depth_limit():
    return max(100, sys.getrecursionlimit() - 100)