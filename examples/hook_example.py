#!/usr/bin/env python3
"""
Hook DLL使用示例
展示如何使用Hook DLL进行稳定的游戏控制
"""

import sys
import os
import time

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from hook_client import HookClient, inject_dll, find_pvz_process


def example_basic_usage():
    """基础使用示例"""
    print("=" * 60)
    print("示例1：基础使用")
    print("=" * 60)
    
    # 查找PVZ进程
    print("1. 查找PVZ进程...")
    pid = find_pvz_process()
    if not pid:
        print("❌ 未找到PVZ进程，请先启动游戏")
        return False
    print(f"✅ 找到PVZ (PID: {pid})")
    
    # 注入DLL
    print("\n2. 注入Hook DLL...")
    if not inject_dll(pid=pid):
        print("❌ 注入失败")
        return False
    print("✅ 注入成功")
    
    # 等待初始化
    print("\n3. 等待初始化...")
    time.sleep(2)
    
    # 连接
    print("\n4. 连接到Hook DLL...")
    with HookClient() as client:
        print("✅ 连接成功")
        
        # 获取状态
        print("\n5. 获取游戏状态...")
        state = client.get_state()
        if state:
            print(f"✅ 状态：")
            print(f"   - 游戏中: {state.get('in_game')}")
            print(f"   - 阳光: {state.get('sun')}")
            print(f"   - 波数: {state.get('wave')}/{state.get('total_waves')}")
            print(f"   - 僵尸: {state.get('zombie_count')}")
            print(f"   - 植物: {state.get('plant_count')}")
        else:
            print("❌ 无法获取状态")
            return False
    
    print("\n✅ 示例完成")
    return True


def example_plant_operations():
    """植物操作示例"""
    print("\n" + "=" * 60)
    print("示例2：植物操作")
    print("=" * 60)
    print("请确保：")
    print("  1. 游戏已进入战斗界面")
    print("  2. 有足够的阳光")
    print("  3. 已选择豌豆射手卡片")
    print()
    
    input("准备好后按回车继续...")
    
    with HookClient() as client:
        # 种植物
        print("\n种植豌豆射手在 (0, 0)...")
        if client.plant(0, 0, 0):
            print("✅ 种植成功")
            time.sleep(2)
            
            # 铲植物
            print("\n铲除 (0, 0) 的植物...")
            if client.shovel(0, 0):
                print("✅ 铲除成功")
            else:
                print("❌ 铲除失败")
        else:
            print("❌ 种植失败（可能阳光不足或卡片冷却中）")


def example_level_control():
    """关卡控制示例"""
    print("\n" + "=" * 60)
    print("示例3：关卡控制")
    print("=" * 60)
    print("请确保游戏已进入战斗界面")
    print()
    
    input("准备好后按回车继续...")
    
    with HookClient() as client:
        # 重置关卡
        print("\n重置关卡...")
        if client.reset():
            print("✅ 重置成功")
            time.sleep(2)
            
            # 检查状态
            state = client.get_state()
            if state:
                print(f"重置后状态：")
                print(f"  - 波数: {state.get('wave')}")
                print(f"  - 阳光: {state.get('sun')}")
                print(f"  - 僵尸: {state.get('zombie_count')}")
                print(f"  - 植物: {state.get('plant_count')}")
        else:
            print("❌ 重置失败")


def example_auto_training_loop():
    """自动训练循环示例"""
    print("\n" + "=" * 60)
    print("示例4：自动训练循环")
    print("=" * 60)
    print("这个示例会持续运行，按Ctrl+C停止")
    print()
    
    input("准备好后按回车继续...")
    
    with HookClient() as client:
        print("\n开始监控...")
        print("-" * 60)
        
        try:
            while True:
                state = client.get_state()
                if not state:
                    print("\r等待游戏状态...", end='', flush=True)
                    time.sleep(0.5)
                    continue
                
                in_game = state.get('in_game')
                sun = state.get('sun', 0)
                wave = state.get('wave', 0)
                zombies = state.get('zombie_count', 0)
                plants = state.get('plant_count', 0)
                
                # 显示状态
                print(f"\r游戏: {'是' if in_game else '否'} | "
                      f"阳光: {sun:4d} | "
                      f"波数: {wave:2d} | "
                      f"僵尸: {zombies:3d} | "
                      f"植物: {plants:3d}",
                      end='', flush=True)
                
                if in_game:
                    # 简单的AI逻辑示例
                    # 如果阳光够，在前排种豌豆射手
                    if sun >= 100 and plants < 5:
                        row = plants % 5
                        col = 0
                        if client.plant(row, col, 0):
                            print(f"\n  → 种植豌豆射手在 ({row}, {col})")
                
                time.sleep(0.5)
                
        except KeyboardInterrupt:
            print("\n\n停止训练")


def main():
    """主函数"""
    print("=" * 60)
    print("  PVZ Hook DLL 使用示例")
    print("=" * 60)
    print()
    
    examples = [
        ("基础使用", example_basic_usage),
        ("植物操作", example_plant_operations),
        ("关卡控制", example_level_control),
        ("自动训练循环", example_auto_training_loop),
    ]
    
    while True:
        print("\n请选择示例：")
        for i, (name, _) in enumerate(examples, 1):
            print(f"  {i}. {name}")
        print("  0. 退出")
        print()
        
        try:
            choice = input("选择 (0-4): ").strip()
            if choice == '0':
                print("再见！")
                break
            
            idx = int(choice) - 1
            if 0 <= idx < len(examples):
                name, func = examples[idx]
                func()
            else:
                print("无效选择")
        except ValueError:
            print("无效输入")
        except KeyboardInterrupt:
            print("\n\n再见！")
            break


if __name__ == "__main__":
    main()
