"""
设置冒险模式关卡

用法：
    python set_level.py 1      # 设置为 1-1
    python set_level.py 3      # 设置为 1-3
    python set_level.py 11     # 设置为 2-1 (夜间)
"""

import sys
sys.path.insert(0, '.')

from main import PVZMemoryInterface

def main():
    level = 1
    if len(sys.argv) > 1:
        level = int(sys.argv[1])
    
    print(f"设置冒险模式关卡为: {level}")
    
    # 计算显示名称
    world = (level - 1) // 10 + 1
    stage = (level - 1) % 10 + 1
    print(f"对应关卡: {world}-{stage}")
    
    pvz = PVZMemoryInterface()
    
    if not pvz.attach():
        print("❌ 无法连接到 PVZ 进程，请确保游戏正在运行")
        return
    
    if pvz.set_adventure_level(level):
        print(f"✅ 成功设置关卡为 {world}-{stage}")
        print("请返回主菜单，然后点击冒险模式即可进入该关卡")
    else:
        print("❌ 设置失败")

if __name__ == "__main__":
    main()
