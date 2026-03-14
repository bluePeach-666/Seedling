import platform
import sys

def get_system_mem_limit_mb():
    fallback_mb = 512
    try:
        system = platform.system()
        if system == "Linux":
            with open('/proc/meminfo', 'r') as f:
                for line in f:
                    if 'MemTotal' in line:
                        kb = int(line.split()[1])
                        return max(fallback_mb, int((kb / 1024) * 0.10))
                        
        elif system == "Darwin": # macOS
            import subprocess
            out = subprocess.check_output(['sysctl', '-n', 'hw.memsize']).decode('utf-8')
            bytes_mem = int(out.strip())
            return max(fallback_mb, int((bytes_mem / (1024 * 1024)) * 0.10))
            
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
                return max(fallback_mb, int((stat.ullTotalPhys / (1024 * 1024)) * 0.10))
            
    except Exception:
        pass
        
    return fallback_mb

def get_system_depth_limit():
    return max(100, sys.getrecursionlimit() - 100)