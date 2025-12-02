"""
调试重置功能
"""

import sys
import struct
import ctypes
from ctypes import wintypes
sys.path.insert(0, '.')

from main import PVZMemoryInterface
from data.offsets import Offset

def main():
    print("调试重置功能...")
    
    pvz = PVZMemoryInterface()
    
    if not pvz.attach():
        print("❌ 无法连接到 PVZ 进程")
        return
    
    print(f"✅ 已连接到 PVZ (PID: {pvz.pid})")
    
    # 检查游戏状态
    base = pvz.reader.read_int(Offset.BASE)
    print(f"Base: 0x{base:X}")
    
    if base:
        game_ui = pvz.reader.read_int(base + Offset.GAME_UI)
        print(f"Game UI: {game_ui} (3=游戏中, 2=选卡)")
        
        board = pvz.reader.read_int(base + Offset.MAIN_OBJECT)
        print(f"Board: 0x{board:X}")
        
        if board:
            sun = pvz.reader.read_int(board + Offset.SUN)
            wave = pvz.reader.read_int(board + Offset.WAVE)
            total_waves = pvz.reader.read_int(board + Offset.TOTAL_WAVE)
            scene = pvz.reader.read_int(board + Offset.SCENE)
            print(f"Sun: {sun}")
            print(f"Wave: {wave}/{total_waves}")
            print(f"Scene: {scene}")
    
    print("\n尝试手动执行 shellcode...")
    
    # 测试简单的 shellcode 先
    injector = pvz.injector
    
    # 先测试能否分配内存
    test_addr = injector.alloc_memory(64)
    if test_addr:
        print(f"✅ 内存分配成功: 0x{test_addr:X}")
        injector.free_memory(test_addr)
    else:
        print("❌ 内存分配失败")
        return
    
    # 尝试一个简单的 shellcode (只返回)
    simple_shellcode = bytes([0xC3])  # ret
    result = injector.execute_shellcode(simple_shellcode)
    print(f"简单 shellcode 测试: {result}")
    
    if not result:
        print("❌ 基础 shellcode 执行失败，可能需要管理员权限")
        return
    
    # 尝试调用 MakeNewBoard
    print("\n调用 MakeNewBoard...")
    
    # 简化的 shellcode - 只调用 MakeNewBoard
    shellcode = bytes([
        # mov ecx, [0x6a9ec0]
        0x8B, 0x0D, *struct.pack('<I', Offset.BASE),
        
        # mov eax, 0x44f5f0
        0xB8, *struct.pack('<I', 0x44F5F0),
        
        # call eax
        0xFF, 0xD0,
        
        # ret
        0xC3
    ])
    
    print(f"Shellcode 长度: {len(shellcode)}")
    print(f"Shellcode: {shellcode.hex()}")
    
    result = injector.execute_shellcode(shellcode, timeout=5000)
    print(f"MakeNewBoard 执行结果: {result}")
    
    if result:
        # 再次读取状态
        import time
        time.sleep(0.5)
        board = pvz.reader.read_int(base + Offset.MAIN_OBJECT)
        if board:
            sun = pvz.reader.read_int(board + Offset.SUN)
            wave = pvz.reader.read_int(board + Offset.WAVE)
            print(f"\n重置后:")
            print(f"Sun: {sun}")
            print(f"Wave: {wave}")

if __name__ == "__main__":
    main()
