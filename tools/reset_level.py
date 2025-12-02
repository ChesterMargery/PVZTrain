"""
重置当前关卡（生存模式回到第一天）

用法：
    python reset_level.py
"""

import sys
sys.path.insert(0, '.')

from main import PVZMemoryInterface
import time

def main():
    print("重置当前关卡...")
    
    pvz = PVZMemoryInterface()
    
    if not pvz.attach():
        print("❌ 无法连接到 PVZ 进程，请确保游戏正在运行")
        return
    
    if not pvz.is_in_game():
        print("❌ 请先进入一个关卡")
        return
    
    print("调用 MakeNewBoard()...")
    
    if pvz.restart_level():
        print("✅ 重置成功！关卡已回到开始状态")
    else:
        print("❌ 重置失败")

if __name__ == "__main__":
    main()
