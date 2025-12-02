"""
模型选择与性能基准测试

基于文献研究结果:
1. PPO (Schulman et al., 2017) - 稳定、易调参、适合离散动作
2. DQN (Mnih et al., 2013) - 经典、离散动作专用、样本效率高
3. A2C (Mnih et al., 2016) - 并行化好、但不如PPO稳定

文献支持:
- PPO: "outperforms other online policy gradient methods, and overall strikes 
        a favorable balance between sample complexity, simplicity, and wall-time"
- DQN: "substantially more sample efficient when they do work, because they 
        can reuse data more effectively"
- 结论: 对于离散动作空间的游戏，PPO和DQN都是好选择
       PPO更稳定易调，DQN样本效率更高

参考:
- https://arxiv.org/abs/1707.06347 (PPO)
- https://arxiv.org/abs/1312.5602 (DQN)
- https://spinningup.openai.com/en/latest/spinningup/rl_intro2.html
- https://stable-baselines3.readthedocs.io/en/master/guide/algos.html
"""

import time
import torch
import numpy as np
from typing import Dict, Tuple

# 检查CUDA是否可用
def check_hardware() -> Dict:
    """检查硬件配置"""
    info = {
        'cuda_available': torch.cuda.is_available(),
        'cuda_device': None,
        'cuda_memory_gb': None,
        'cpu_count': torch.get_num_threads(),
    }
    
    if info['cuda_available']:
        info['cuda_device'] = torch.cuda.get_device_name(0)
        info['cuda_memory_gb'] = torch.cuda.get_device_properties(0).total_memory / (1024**3)
    
    return info


def benchmark_device(device: str, iterations: int = 1000, 
                     batch_size: int = 64, hidden_size: int = 128) -> Dict:
    """
    测试特定设备的计算性能
    
    模拟PPO/DQN的典型网络前向传播
    """
    # 模拟PVZ状态输入
    # 6x9网格 + 僵尸数据(假设最多20个) + 全局状态
    state_dim = 6 * 9 + 20 * 10 + 20  # = 274
    action_dim = 48 * 54  # 植物类型 * 位置 (简化)
    
    # 创建简单的MLP网络 (模拟PPO/DQN的策略网络)
    model = torch.nn.Sequential(
        torch.nn.Linear(state_dim, hidden_size),
        torch.nn.ReLU(),
        torch.nn.Linear(hidden_size, hidden_size),
        torch.nn.ReLU(),
        torch.nn.Linear(hidden_size, action_dim),
    ).to(device)
    
    # 创建测试数据
    x = torch.randn(batch_size, state_dim, device=device)
    
    # 预热
    for _ in range(10):
        _ = model(x)
    
    if device == 'cuda':
        torch.cuda.synchronize()
    
    # 计时 - 前向传播
    start = time.perf_counter()
    for _ in range(iterations):
        _ = model(x)
    
    if device == 'cuda':
        torch.cuda.synchronize()
    
    forward_time = (time.perf_counter() - start) / iterations * 1000  # ms
    
    # 计时 - 前向+后向传播 (训练)
    optimizer = torch.optim.Adam(model.parameters(), lr=3e-4)
    target = torch.randn(batch_size, action_dim, device=device)
    
    start = time.perf_counter()
    for _ in range(iterations):
        optimizer.zero_grad()
        output = model(x)
        loss = torch.nn.functional.mse_loss(output, target)
        loss.backward()
        optimizer.step()
    
    if device == 'cuda':
        torch.cuda.synchronize()
    
    train_time = (time.perf_counter() - start) / iterations * 1000  # ms
    
    return {
        'device': device,
        'forward_ms': forward_time,
        'train_ms': train_time,
        'batch_size': batch_size,
        'hidden_size': hidden_size,
        'throughput_forward': batch_size / forward_time * 1000,  # samples/s
        'throughput_train': batch_size / train_time * 1000,  # samples/s
    }


def benchmark_batch_sizes(device: str) -> list:
    """测试不同batch size的性能"""
    results = []
    for bs in [16, 32, 64, 128, 256]:
        try:
            result = benchmark_device(device, iterations=500, batch_size=bs)
            results.append(result)
        except RuntimeError as e:
            if 'out of memory' in str(e).lower():
                print(f"  Batch size {bs}: OOM")
                break
            raise
    return results


def recommend_config(cpu_result: Dict, gpu_result: Dict = None) -> Dict:
    """根据测试结果推荐配置"""
    
    # 判断是否值得用GPU
    use_gpu = False
    reason = ""
    
    if gpu_result:
        speedup = cpu_result['train_ms'] / gpu_result['train_ms']
        if speedup > 1.5:
            use_gpu = True
            reason = f"GPU比CPU快{speedup:.1f}倍"
        else:
            reason = f"GPU加速不明显({speedup:.1f}x)，建议用CPU省显存"
    else:
        reason = "无可用GPU"
    
    # 推荐参数
    config = {
        'device': 'cuda' if use_gpu else 'cpu',
        'reason': reason,
        'algorithm': 'PPO',  # 默认推荐
        'algorithm_reason': '稳定、易调参、适合离散动作空间',
        'batch_size': 64,
        'n_steps': 512,
        'learning_rate': 3e-4,
        'net_arch': [128, 128],
        'n_epochs': 10,
    }
    
    # 如果用GPU且显存足够，可以增大batch
    if use_gpu and gpu_result:
        # 根据测试结果调整
        config['batch_size'] = 128
    
    return config


def print_results(hw_info: Dict, cpu_results: list, gpu_results: list, recommendation: Dict):
    """打印测试结果"""
    print("=" * 60)
    print("PVZ 强化学习模型基准测试")
    print("=" * 60)
    
    print("\n【硬件信息】")
    print(f"  CPU 线程数: {hw_info['cpu_count']}")
    if hw_info['cuda_available']:
        print(f"  GPU: {hw_info['cuda_device']}")
        print(f"  显存: {hw_info['cuda_memory_gb']:.1f} GB")
    else:
        print("  GPU: 不可用")
    
    print("\n【CPU 性能测试】")
    print("  Batch Size | 前向(ms) | 训练(ms) | 吞吐量(samples/s)")
    print("  " + "-" * 55)
    for r in cpu_results:
        print(f"  {r['batch_size']:>10} | {r['forward_ms']:>8.2f} | {r['train_ms']:>8.2f} | {r['throughput_train']:>12.0f}")
    
    if gpu_results:
        print("\n【GPU 性能测试】")
        print("  Batch Size | 前向(ms) | 训练(ms) | 吞吐量(samples/s)")
        print("  " + "-" * 55)
        for r in gpu_results:
            print(f"  {r['batch_size']:>10} | {r['forward_ms']:>8.2f} | {r['train_ms']:>8.2f} | {r['throughput_train']:>12.0f}")
    
    print("\n【推荐配置】")
    print(f"  设备: {recommendation['device']}")
    print(f"  原因: {recommendation['reason']}")
    print(f"  算法: {recommendation['algorithm']}")
    print(f"  算法原因: {recommendation['algorithm_reason']}")
    print("\n  参数配置:")
    print(f"    batch_size = {recommendation['batch_size']}")
    print(f"    n_steps = {recommendation['n_steps']}")
    print(f"    learning_rate = {recommendation['learning_rate']}")
    print(f"    net_arch = {recommendation['net_arch']}")
    print(f"    n_epochs = {recommendation['n_epochs']}")
    
    print("\n【文献支持】")
    print("  PPO (Schulman et al., 2017):")
    print("    - arXiv:1707.06347")
    print("    - 'strikes a favorable balance between sample complexity,")
    print("       simplicity, and wall-time'")
    print("  DQN (Mnih et al., 2013):")
    print("    - arXiv:1312.5602")
    print("    - 适合纯离散动作，样本效率更高")
    print("  OpenAI Spinning Up:")
    print("    - PPO更稳定可靠，DQN可能不稳定但样本效率高")
    print("    - 对于游戏类任务，两者都是好选择")
    
    print("\n" + "=" * 60)


def main():
    """运行基准测试"""
    print("正在检测硬件...")
    hw_info = check_hardware()
    
    print("正在测试CPU性能...")
    cpu_results = benchmark_batch_sizes('cpu')
    
    gpu_results = []
    if hw_info['cuda_available']:
        print("正在测试GPU性能...")
        gpu_results = benchmark_batch_sizes('cuda')
    
    # 用batch_size=64的结果做比较
    cpu_64 = next((r for r in cpu_results if r['batch_size'] == 64), cpu_results[-1])
    gpu_64 = next((r for r in gpu_results if r['batch_size'] == 64), None) if gpu_results else None
    
    recommendation = recommend_config(cpu_64, gpu_64)
    
    print_results(hw_info, cpu_results, gpu_results, recommendation)
    
    return recommendation


if __name__ == "__main__":
    config = main()
