"""
测试 PVZ Gym 环境

使用方法:
1. 启动 PVZ 游戏
2. 进入一个关卡 (冒险模式或生存模式)
3. 运行此脚本

python test_env.py          # 随机动作测试
python test_env.py --ppo    # 用PPO训练
"""

import argparse
import time
import numpy as np

def test_random_actions(steps: int = 100):
    """用随机动作测试环境"""
    print("=" * 50)
    print("PVZ 环境测试 - 随机动作")
    print("=" * 50)
    
    from env import PVZEnv
    
    print("\n创建环境...")
    env = PVZEnv(render_mode="human", auto_collect=True)
    
    print("重置环境 (请确保游戏已进入关卡)...")
    try:
        obs, info = env.reset()
        print(f"初始观察向量大小: {obs.shape}")
        print(f"初始信息: {info}")
    except RuntimeError as e:
        print(f"错误: {e}")
        return
    
    print(f"\n开始测试 {steps} 步随机动作...")
    print("-" * 50)
    
    for step in range(steps):
        # 随机动作
        action = env.action_space.sample()
        
        # 执行
        obs, reward, terminated, truncated, info = env.step(action)
        
        # 渲染
        env.render()
        
        # 检查结束
        if terminated or truncated:
            print(f"\n游戏结束! 步数: {step + 1}, 总奖励: {info['total_reward']:.1f}")
            break
        
        # 每10步打印动作
        if step % 10 == 0:
            seed_slot, row, col = action
            if seed_slot == 0:
                print(f"  Step {step}: 等待")
            else:
                print(f"  Step {step}: 种植卡槽{seed_slot} 在 ({row}, {col})")
    
    print("\n测试完成!")
    env.close()


def test_observation_only():
    """只测试观察向量的生成"""
    print("=" * 50)
    print("PVZ 环境测试 - 观察向量")
    print("=" * 50)
    
    from env import PVZEnv
    
    env = PVZEnv()
    
    try:
        obs, info = env.reset()
    except RuntimeError as e:
        print(f"错误: {e}")
        return
    
    print(f"\n观察向量:")
    print(f"  形状: {obs.shape}")
    print(f"  最小值: {obs.min():.4f}")
    print(f"  最大值: {obs.max():.4f}")
    print(f"  均值: {obs.mean():.4f}")
    
    print(f"\n游戏状态:")
    for k, v in info.items():
        print(f"  {k}: {v}")
    
    # 分解观察向量
    print(f"\n观察向量分解:")
    idx = 0
    print(f"  [0:3] 全局状态: {obs[idx:idx+3]}")
    idx += 3
    
    grid_size = 6 * 9
    grid = obs[idx:idx+grid_size].reshape(6, 9)
    print(f"  [3:{3+grid_size}] 植物网格 (非零位置):")
    for r in range(6):
        for c in range(9):
            if grid[r, c] > 0:
                print(f"    ({r}, {c}): {grid[r, c]:.2f}")
    idx += grid_size
    
    zombie_size = 50 * 5
    zombies = obs[idx:idx+zombie_size].reshape(50, 5)
    active_zombies = (zombies[:, 0] > 0).sum()
    print(f"  [{3+grid_size}:...] 活跃僵尸数: {active_zombies}")
    
    env.close()


def train_ppo(timesteps: int = 10000):
    """用PPO训练"""
    print("=" * 50)
    print("PVZ PPO 训练")
    print("=" * 50)
    
    try:
        from stable_baselines3 import PPO
        from stable_baselines3.common.callbacks import BaseCallback
    except ImportError:
        print("需要安装 stable-baselines3:")
        print("  pip install stable-baselines3")
        return
    
    from env import PVZEnv
    
    # 自定义回调打印进度
    class PrintCallback(BaseCallback):
        def __init__(self, print_freq=100):
            super().__init__()
            self.print_freq = print_freq
        
        def _on_step(self):
            if self.n_calls % self.print_freq == 0:
                if len(self.model.ep_info_buffer) > 0:
                    ep_info = self.model.ep_info_buffer[-1]
                    print(f"Step {self.n_calls}: reward={ep_info.get('r', 0):.1f}")
            return True
    
    print("\n创建环境...")
    env = PVZEnv(auto_collect=True, discrete_action=False)  # PPO uses MultiDiscrete
    
    print("创建PPO模型...")
    model = PPO(
        "MlpPolicy",
        env,
        learning_rate=3e-4,
        n_steps=512,
        batch_size=64,
        n_epochs=10,
        policy_kwargs=dict(net_arch=[128, 128]),
        verbose=1,
        device="cuda",  # 改成 "cpu" 如果GPU有问题
    )
    
    print(f"\n开始训练 {timesteps} 步...")
    print("请确保游戏已进入关卡!")
    print("-" * 50)
    
    try:
        model.learn(
            total_timesteps=timesteps,
            callback=PrintCallback(print_freq=100),
        )
    except KeyboardInterrupt:
        print("\n训练被中断")
    except Exception as e:
        print(f"\n训练出错: {e}")
    finally:
        # 无论如何都保存模型
        model.save("ppo_pvz")
        print("\n模型已保存到 ppo_pvz.zip")
        env.close()


def train_dqn(timesteps: int = 100000):
    """用DQN训练 - 更适合PVZ这种离散动作游戏"""
    print("=" * 50)
    print("PVZ DQN 训练")
    print("=" * 50)
    
    try:
        from stable_baselines3 import DQN
        from stable_baselines3.common.callbacks import BaseCallback
    except ImportError:
        print("需要安装 stable-baselines3:")
        print("  pip install stable-baselines3")
        return
    
    from env import PVZEnv
    
    # 自定义回调打印进度
    class PrintCallback(BaseCallback):
        def __init__(self, print_freq=50, detail_freq=500):
            super().__init__()
            self.print_freq = print_freq
            self.detail_freq = detail_freq
            self.last_ep_count = 0
        
        def _on_step(self):
            # 实时显示每一步的奖励
            infos = self.locals.get('infos', [{}])
            rewards = self.locals.get('rewards', [0])
            
            # 每 print_freq 步显示一次简要信息
            if self.n_calls % self.print_freq == 0:
                info = infos[0] if infos else {}
                reward = rewards[0] if len(rewards) > 0 else 0
                sun = info.get('sun', '?')
                wave = info.get('wave', '?')
                zombies = info.get('zombie_count', '?')
                eps = info.get('exploration_rate', self.model.exploration_rate) if hasattr(self.model, 'exploration_rate') else '?'
                print(f"[Step {self.n_calls}] r={reward:+.2f} | sun={sun} wave={wave} zombies={zombies} | eps={eps:.2f}")
            
            # Episode 完成时显示总结
            if len(self.model.ep_info_buffer) > self.last_ep_count:
                self.last_ep_count = len(self.model.ep_info_buffer)
                ep_info = self.model.ep_info_buffer[-1]
                print(f"\n{'='*50}")
                print(f"Episode {self.last_ep_count} 完成: 总奖励={ep_info.get('r', 0):.1f}, 步数={ep_info.get('l', 0)}")
                print(f"{'='*50}\n")
            
            return True
    
    print("\n创建环境...")
    env = PVZEnv(auto_collect=True, discrete_action=True)  # DQN uses Discrete
    
    print("创建DQN模型...")
    model = DQN(
        "MlpPolicy",
        env,
        learning_rate=1e-4,
        buffer_size=50000,           # 经验回放缓冲区
        learning_starts=1000,         # 先收集1000步再开始学习
        batch_size=128,              # RTX 3050 测试最优
        tau=0.005,                    # 软更新目标网络
        gamma=0.99,                   # 折扣因子
        train_freq=4,                 # 每4步训练一次
        gradient_steps=1,
        target_update_interval=1000,  # 每1000步更新目标网络
        exploration_fraction=0.3,     # 前30%时间探索
        exploration_initial_eps=1.0,  # 初始探索率100%
        exploration_final_eps=0.05,   # 最终探索率5%
        policy_kwargs=dict(net_arch=[256, 256]),  # 更大的网络
        verbose=1,
        device="cuda",  # 改成 "cpu" 如果GPU有问题
    )
    
    print(f"\n开始训练 {timesteps} 步...")
    print("请确保游戏已进入关卡!")
    print("DQN 前1000步只收集数据，之后开始学习")
    print("-" * 50)
    
    try:
        model.learn(
            total_timesteps=timesteps,
            callback=PrintCallback(print_freq=500),
        )
    except KeyboardInterrupt:
        print("\n训练被中断")
    except Exception as e:
        print(f"\n训练出错: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # 无论如何都保存模型
        model.save("dqn_pvz")
        print("\n模型已保存到 dqn_pvz.zip")
        env.close()


def main():
    parser = argparse.ArgumentParser(description="测试PVZ Gym环境")
    parser.add_argument("--ppo", action="store_true", help="用PPO训练")
    parser.add_argument("--dqn", action="store_true", help="用DQN训练 (推荐)")
    parser.add_argument("--obs", action="store_true", help="只测试观察向量")
    parser.add_argument("--steps", type=int, default=100, help="测试步数")
    parser.add_argument("--timesteps", type=int, default=100000, help="训练步数")
    
    args = parser.parse_args()
    
    if args.dqn:
        train_dqn(args.timesteps)
    elif args.ppo:
        train_ppo(args.timesteps)
    elif args.obs:
        test_observation_only()
    else:
        test_random_actions(args.steps)


if __name__ == "__main__":
    main()
