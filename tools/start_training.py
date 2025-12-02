#!/usr/bin/env python3
"""
一键启动训练脚本
使用Hook DLL实现稳定的自动化训练
"""

import sys
import os
import time
import argparse

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from hook_client import HookClient, inject_dll, find_pvz_process


def main():
    parser = argparse.ArgumentParser(description="PVZ训练启动器 (Hook DLL模式)")
    parser.add_argument("--dll", type=str, help="DLL路径 (默认: hook/pvz_hook.dll)")
    parser.add_argument("--no-inject", action="store_true", help="跳过注入 (假设DLL已加载)")
    parser.add_argument("--port", type=int, default=12345, help="Hook DLL端口 (默认: 12345)")
    args = parser.parse_args()
    
    print("=" * 60)
    print("  PVZ训练启动器 (Hook DLL模式)")
    print("=" * 60)
    print()
    
    # 1. 检查PVZ进程
    print("[1/4] 检查PVZ进程...")
    pid = find_pvz_process()
    if pid is None:
        print("❌ 未找到PVZ进程")
        print("请先启动游戏！")
        return 1
    print(f"✅ 找到PVZ进程: PID={pid}")
    print()
    
    # 2. 注入Hook DLL
    if not args.no_inject:
        print("[2/4] 注入Hook DLL...")
        if not inject_dll(dll_path=args.dll, pid=pid):
            print("❌ DLL注入失败")
            print("可能原因：")
            print("  1. DLL未编译 - 运行 hook/build.bat 编译")
            print("  2. 权限不足 - 以管理员身份运行")
            print("  3. DLL路径错误")
            return 1
        print("✅ DLL注入成功")
        print()
        
        # 等待DLL初始化
        print("等待Hook初始化...")
        time.sleep(2)
    else:
        print("[2/4] 跳过注入 (假设DLL已加载)")
        print()
    
    # 3. 连接到Hook DLL
    print("[3/4] 连接到Hook DLL...")
    client = HookClient(port=args.port)
    
    max_retries = 5
    for i in range(max_retries):
        if client.connect():
            print("✅ 连接成功")
            break
        print(f"⏳ 重试 {i+1}/{max_retries}...")
        time.sleep(1)
    else:
        print("❌ 连接失败")
        print("Hook DLL可能未正确加载")
        print("请检查：")
        print("  1. DLL是否注入成功")
        print(f"  2. 端口{args.port}是否被占用")
        return 1
    print()
    
    # 4. 测试通信
    print("[4/4] 测试通信...")
    state = client.get_state()
    if state is None:
        print("❌ 无法获取游戏状态")
        client.disconnect()
        return 1
    
    print("✅ 通信正常")
    print(f"游戏状态: {state}")
    print()
    
    # 启动成功
    print("=" * 60)
    print("  🎉 启动成功！")
    print("=" * 60)
    print()
    print("现在可以使用HookClient进行训练：")
    print()
    print("示例代码：")
    print("  from hook_client import HookClient")
    print("  client = HookClient()")
    print("  client.plant(0, 0, 0)  # 种植物")
    print("  client.reset()         # 重置关卡")
    print("  state = client.get_state()  # 获取状态")
    print()
    
    # 保持连接，进入简单的监控模式
    print("进入监控模式 (按Ctrl+C退出)...")
    print("-" * 60)
    
    try:
        while True:
            state = client.get_state()
            if state:
                in_game = "是" if state.get('in_game') else "否"
                print(f"\r游戏中: {in_game} | 阳光: {state.get('sun', 0):4d} | "
                      f"波数: {state.get('wave', 0):2d}/{state.get('total_waves', 0):2d} | "
                      f"僵尸: {state.get('zombie_count', 0):3d} | "
                      f"植物: {state.get('plant_count', 0):3d}", end='', flush=True)
            time.sleep(0.5)
    except KeyboardInterrupt:
        print("\n")
        print("正在退出...")
    finally:
        client.disconnect()
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
