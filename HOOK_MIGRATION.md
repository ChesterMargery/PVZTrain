# Hook DLL迁移指南

本文档说明如何从旧的shellcode注入方式迁移到新的Hook DLL方式。

## 为什么要迁移？

旧的Python shellcode注入方式存在严重的时机问题，特别是界面切换（选卡、开始游戏、重置关卡）时容易导致游戏崩溃。

新的Hook DLL方式将所有写内存操作移到游戏进程内部执行，彻底消除崩溃风险。

## 迁移步骤

### 1. 编译Hook DLL

```bash
cd hook
build.bat
```

这会生成 `hook/pvz_hook.dll`。

### 2. 更新代码

#### 旧代码（Legacy模式）

```python
from main import PVZMemoryInterface

memory = PVZMemoryInterface()
memory.attach()

# 种植物
memory.plant(0, 0, 0)

# 重置关卡
memory.restart_level()
```

#### 新代码（Hook模式） - 方案1：使用PVZInterface

```python
from core import PVZInterface, InterfaceMode

# 创建Hook模式接口
pvz = PVZInterface(mode=InterfaceMode.HOOK)
pvz.attach()

# 种植物
pvz.plant(0, 0, 0)

# 重置关卡
pvz.restart_level()
```

#### 新代码（Hook模式） - 方案2：直接使用HookClient

```python
from hook_client import HookClient, inject_dll
import time

# 注入DLL
if inject_dll():
    time.sleep(2)  # 等待初始化
    
    # 连接
    client = HookClient()
    if client.connect():
        # 种植物
        client.plant(0, 0, 0)
        
        # 重置关卡
        client.reset()
        
        # 获取状态
        state = client.get_state()
        print(f"阳光: {state['sun']}")
```

### 3. 启动流程

#### 旧方式

```python
python main.py
```

#### 新方式（推荐）

```bash
# 一键启动
python tools/start_training.py
```

或手动：

```python
from hook_client import inject_dll
from core import PVZInterface, InterfaceMode
import time

# 1. 注入DLL
inject_dll()
time.sleep(2)

# 2. 创建接口
pvz = PVZInterface(mode=InterfaceMode.HOOK)
pvz.attach()

# 3. 开始训练
while True:
    state = pvz.get_game_state()
    if state:
        # 你的逻辑
        pass
```

## API对比

### 种植物

```python
# 旧方式
memory.plant(row, col, plant_type)

# 新方式
pvz.plant(row, col, plant_type)      # PVZInterface
client.plant(row, col, plant_type)   # HookClient
```

### 铲植物

```python
# 旧方式
memory.shovel(row, col)

# 新方式
pvz.shovel(row, col)      # PVZInterface
client.shovel(row, col)   # HookClient
```

### 重置关卡

```python
# 旧方式
memory.restart_level()

# 新方式
pvz.restart_level()   # PVZInterface
client.reset()        # HookClient
```

### 获取状态

```python
# 旧方式
state = memory.get_game_state()

# 新方式（PVZInterface - 完整状态）
state = pvz.get_game_state()

# 新方式（HookClient - 基础状态）
state = client.get_state()
```

## 注意事项

### 1. 自动收集阳光

Hook模式目前不支持自动收集阳光（因为需要在DLL中实现）。

如果需要自动收集，可以暂时使用Legacy模式：

```python
pvz = PVZInterface(mode=InterfaceMode.LEGACY)
```

### 2. DLL注入

Hook DLL需要先注入到游戏进程。有两种方式：

- **自动注入**：使用 `inject_dll()` 函数
- **手动注入**：使用DLL注入工具（如Extreme Injector）

### 3. 端口占用

Hook DLL默认监听端口12345。如果端口被占用，可以：

```python
# 使用其他端口（需要重新编译DLL修改端口）
client = HookClient(port=54321)
```

### 4. 游戏版本

Hook DLL是针对PVZ 1.0.0.1051（中文年度版）开发的。其他版本可能需要调整地址。

## 故障排除

### 连接失败

```
Failed to connect to Hook DLL
```

**可能原因**：
1. DLL未注入 → 运行 `inject_dll()`
2. DLL未编译 → 运行 `hook/build.bat`
3. 端口被占用 → 检查端口12345

### DLL注入失败

```
Failed to inject DLL
```

**可能原因**：
1. 游戏未启动 → 先启动游戏
2. 权限不足 → 以管理员身份运行
3. DLL路径错误 → 检查 `hook/pvz_hook.dll` 是否存在

### 游戏崩溃

如果使用Hook模式仍然崩溃，可能是：
1. DLL版本不匹配 → 重新编译
2. Hook地址错误 → 检查游戏版本
3. DLL有bug → 查看Hook DLL日志

## 兼容性

新代码完全向后兼容。你可以：

1. **保持旧代码不变**（继续使用Legacy模式）
2. **逐步迁移**（新功能用Hook，旧功能用Legacy）
3. **完全迁移**（推荐，获得最佳稳定性）

```python
# 混合使用
pvz_hook = PVZInterface(mode=InterfaceMode.HOOK)    # 用于操作
pvz_legacy = PVZInterface(mode=InterfaceMode.LEGACY)  # 用于收集阳光
```

## 推荐配置

对于新项目，推荐使用：

```python
from core import PVZInterface, InterfaceMode
from hook_client import inject_dll
import time

# 注入DLL
print("注入Hook DLL...")
if not inject_dll():
    print("注入失败，请检查游戏是否启动")
    exit(1)

time.sleep(2)

# 创建接口
pvz = PVZInterface(mode=InterfaceMode.HOOK)
if not pvz.attach():
    print("连接失败")
    exit(1)

print("准备就绪！")

# 你的训练循环
while True:
    state = pvz.get_game_state()
    if state:
        # 训练逻辑
        pass
    time.sleep(0.1)
```

## 性能对比

| 特性 | Legacy模式 | Hook模式 |
|------|-----------|---------|
| 稳定性 | ⚠️ 低（易崩溃） | ✅ 高（无崩溃） |
| 速度 | 🐢 慢（跨进程） | 🚀 快（进程内） |
| 实现复杂度 | 复杂（shellcode） | 简单（函数调用） |
| 调试难度 | 高 | 低 |
| 推荐使用 | ❌ | ✅ |

## 更多资源

- [Hook DLL文档](hook/README.md)
- [Hook Client文档](hook_client/README.md)
- [启动脚本](tools/start_training.py)
