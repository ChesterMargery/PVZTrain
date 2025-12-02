"""
DLL Injector
使用CreateRemoteThread注入Hook DLL
"""

import os
import ctypes
from ctypes import wintypes
import psutil
from typing import Optional


# Windows API常量
PROCESS_ALL_ACCESS = 0x1F0FFF
MEM_COMMIT = 0x1000
MEM_RESERVE = 0x2000
MEM_RELEASE = 0x8000
PAGE_READWRITE = 0x04


def find_pvz_process() -> Optional[int]:
    """
    查找PVZ进程
    
    Returns:
        进程ID，未找到返回None
    """
    for proc in psutil.process_iter(['pid', 'name']):
        try:
            name = proc.info['name'].lower()
            if 'plantsvszombies' in name or 'popcapgame1' in name:
                return proc.info['pid']
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    return None


def inject_dll(dll_path: Optional[str] = None, pid: Optional[int] = None) -> bool:
    """
    注入DLL到PVZ进程
    
    Args:
        dll_path: DLL路径，默认为hook/pvz_hook.dll
        pid: 目标进程ID，默认自动查找
        
    Returns:
        True if successful
    """
    # 查找DLL路径
    if dll_path is None:
        # 默认路径
        script_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        dll_path = os.path.join(script_dir, 'hook', 'pvz_hook.dll')
    
    if not os.path.exists(dll_path):
        print(f"DLL not found: {dll_path}")
        print("Please build the DLL first using hook/build.bat")
        return False
    
    # 转换为绝对路径
    dll_path = os.path.abspath(dll_path)
    
    # 查找PVZ进程
    if pid is None:
        pid = find_pvz_process()
        if pid is None:
            print("PVZ process not found!")
            print("Please start the game first.")
            return False
    
    print(f"Found PVZ process: PID={pid}")
    print(f"Injecting DLL: {dll_path}")
    
    # 获取kernel32
    kernel32 = ctypes.WinDLL('kernel32', use_last_error=True)
    
    # 打开目标进程
    hProcess = kernel32.OpenProcess(PROCESS_ALL_ACCESS, False, pid)
    if not hProcess:
        print(f"Failed to open process: {ctypes.get_last_error()}")
        return False
    
    try:
        # 在目标进程中分配内存
        dll_path_bytes = dll_path.encode('utf-8') + b'\x00'
        dll_path_len = len(dll_path_bytes)
        
        pDllPath = kernel32.VirtualAllocEx(
            hProcess, None, dll_path_len,
            MEM_COMMIT | MEM_RESERVE, PAGE_READWRITE
        )
        
        if not pDllPath:
            print(f"Failed to allocate memory: {ctypes.get_last_error()}")
            return False
        
        # 写入DLL路径
        written = ctypes.c_size_t()
        if not kernel32.WriteProcessMemory(
            hProcess, pDllPath, dll_path_bytes, dll_path_len, ctypes.byref(written)
        ):
            print(f"Failed to write memory: {ctypes.get_last_error()}")
            kernel32.VirtualFreeEx(hProcess, pDllPath, 0, MEM_RELEASE)
            return False
        
        # 获取LoadLibraryA地址
        hKernel32 = kernel32.GetModuleHandleW("kernel32.dll")
        pLoadLibraryA = kernel32.GetProcAddress(hKernel32, b"LoadLibraryA")
        
        if not pLoadLibraryA:
            print(f"Failed to get LoadLibraryA: {ctypes.get_last_error()}")
            kernel32.VirtualFreeEx(hProcess, pDllPath, 0, MEM_RELEASE)
            return False
        
        # 创建远程线程
        thread_id = wintypes.DWORD()
        hThread = kernel32.CreateRemoteThread(
            hProcess, None, 0, pLoadLibraryA, pDllPath, 0, ctypes.byref(thread_id)
        )
        
        if not hThread:
            print(f"Failed to create remote thread: {ctypes.get_last_error()}")
            kernel32.VirtualFreeEx(hProcess, pDllPath, 0, MEM_RELEASE)
            return False
        
        # 等待线程完成
        kernel32.WaitForSingleObject(hThread, 5000)  # 5秒超时
        
        # 清理
        kernel32.CloseHandle(hThread)
        kernel32.VirtualFreeEx(hProcess, pDllPath, 0, MEM_RELEASE)
        
        print("DLL injected successfully!")
        print("Hook DLL should be listening on port 12345")
        return True
        
    finally:
        kernel32.CloseHandle(hProcess)


if __name__ == '__main__':
    # 测试注入
    import time
    
    print("PVZ Hook DLL Injector")
    print("=" * 50)
    
    if inject_dll():
        print("\nWaiting for hook to initialize...")
        time.sleep(1)
        
        # 测试连接
        from .client import HookClient
        client = HookClient()
        if client.connect():
            print("Successfully connected to Hook DLL!")
            state = client.get_state()
            if state:
                print(f"Game state: {state}")
            client.disconnect()
        else:
            print("Failed to connect to Hook DLL")
            print("The DLL may not have loaded correctly")
    else:
        print("\nInjection failed!")
