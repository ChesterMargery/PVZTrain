# PVZTrain

基于Hook DLL的稳定PVZ（植物大战僵尸）自动化训练框架。

## 特性

- ✅ **零崩溃** - Hook DLL方式在游戏主线程执行，无时机问题
- 🚀 **高性能** - 进程内执行，减少跨进程通信开销
- 🎯 **完整API** - 支持种植、铲除、重置、状态读取等所有操作
- 🔧 **易于使用** - 提供Python客户端，简单易用
- 📊 **状态监控** - 实时读取游戏状态（阳光、波数、僵尸、植物）
- 🔄 **向后兼容** - 保留传统shellcode模式，支持逐步迁移

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 编译Hook DLL

```bash
cd hook
build.bat
```

需要：
- Visual Studio 2022（或更高版本）
- CMake 3.15+
- Windows SDK

### 3. 运行示例

```bash
# 启动游戏
# 然后运行：
python examples/hook_example.py
```

或使用一键启动脚本：

```bash
python tools/start_training.py
```

## 使用方法

### 方式1：使用PVZInterface（推荐）

```python
from core import PVZInterface, InterfaceMode
from hook_client import inject_dll
import time

# 注入Hook DLL
inject_dll()
time.sleep(2)

# 创建接口
pvz = PVZInterface(mode=InterfaceMode.HOOK)
pvz.attach()

# 获取状态
state = pvz.get_game_state()
print(f"阳光: {state.sun}, 波数: {state.wave}")

# 种植物
pvz.plant(row=0, col=0, plant_type=0)

# 铲植物
pvz.shovel(row=0, col=0)

# 重置关卡
pvz.restart_level()
```

### 方式2：直接使用HookClient

```python
from hook_client import HookClient, inject_dll
import time

# 注入并连接
inject_dll()
time.sleep(2)

with HookClient() as client:
    # 获取状态
    state = client.get_state()
    
    # 种植物
    client.plant(0, 0, 0)
    
    # 重置关卡
    client.reset()
```

## 项目结构

```
PVZTrain/
├── hook/                    # Hook DLL (C++)
│   ├── src/                # 源代码
│   │   ├── dllmain.cpp    # DLL入口
│   │   ├── game.cpp       # 游戏函数
│   │   ├── bridge.cpp     # TCP服务器
│   │   └── state.cpp      # 状态序列化
│   ├── CMakeLists.txt     # CMake配置
│   ├── build.bat          # 编译脚本
│   └── README.md          # 文档
├── hook_client/            # Python客户端
│   ├── client.py          # TCP客户端
│   ├── injector.py        # DLL注入器
│   ├── protocol.py        # 协议定义
│   └── README.md          # 文档
├── core/                   # 核心接口
│   └── pvz.py             # 统一接口（支持Hook/Legacy）
├── memory/                 # 内存操作（Legacy）
├── game/                   # 游戏状态
├── data/                   # 数据定义
├── tools/                  # 工具脚本
├── examples/               # 示例代码
└── main.py                # 传统入口（Legacy模式）
```

## API文档

### HookClient

```python
client = HookClient(host='127.0.0.1', port=12345)

# 连接
client.connect() -> bool
client.disconnect()

# 操作
client.plant(row, col, plant_type) -> bool
client.shovel(row, col) -> bool
client.fire_cob(x, y) -> bool
client.reset() -> bool
client.enter_game(mode) -> bool
client.choose_card(plant_type) -> bool
client.rock() -> bool
client.back_to_main() -> bool

# 状态
client.get_state() -> dict
```

### PVZInterface

```python
pvz = PVZInterface(mode=InterfaceMode.HOOK)

# 连接
pvz.attach() -> bool
pvz.is_attached() -> bool
pvz.is_in_game() -> bool

# 操作
pvz.plant(row, col, plant_type) -> bool
pvz.shovel(row, col) -> bool
pvz.restart_level() -> bool

# 状态
pvz.get_game_state() -> GameState
```

## 迁移指南

如果你正在使用旧的shellcode注入方式，请参考 [迁移指南](HOOK_MIGRATION.md)。

## 故障排除

### DLL注入失败

```python
# 检查游戏是否运行
from hook_client import find_pvz_process
pid = find_pvz_process()
print(f"PVZ PID: {pid}")

# 手动指定DLL路径
inject_dll(dll_path="path/to/pvz_hook.dll")
```

### 连接失败

```python
# 检查端口是否监听
# 在命令行运行：netstat -an | findstr 12345

# 尝试使用其他端口
client = HookClient(port=54321)
```

### 游戏崩溃

如果使用Hook模式仍然崩溃：
1. 确认游戏版本为 PVZ 1.0.0.1051（中文年度版）
2. 重新编译DLL
3. 检查是否有其他修改器冲突

## 支持的游戏版本

- ✅ Plants vs. Zombies 1.0.0.1051（中文年度版）
- ⚠️ 其他版本可能需要调整内存地址

## 依赖

- Python 3.7+
- numpy >= 1.21.0
- pymem >= 1.13.0
- psutil >= 5.9.0

编译DLL需要：
- Visual Studio 2022
- CMake 3.15+
- Windows SDK

## 参考项目

本项目参考了以下优秀项目：

- [AsmVsZombies (AVZ)](https://github.com/vector-wlc/AsmVsZombies) - 游戏函数地址和实现参考
- [re-plants-vs-zombies](https://github.com/calcitem/re-plants-vs-zombies) - 游戏结构参考

## 许可证

MIT License

## 贡献

欢迎提交Issue和Pull Request！

## 常见问题

### Q: Hook模式和Legacy模式有什么区别？

A: Hook模式在游戏进程内执行操作，稳定无崩溃；Legacy模式使用shellcode注入，有时机问题容易崩溃。推荐使用Hook模式。

### Q: 为什么Hook模式不支持自动收集阳光？

A: 当前版本的Hook DLL未实现自动收集功能。可以通过以下方式添加：
1. 在DLL中实现收集功能
2. 或使用Legacy模式的auto_collect

### Q: 可以同时使用Hook和Legacy模式吗？

A: 可以，但不推荐。建议统一使用Hook模式以获得最佳稳定性。

### Q: 如何调试Hook DLL？

A: 可以在DLL中添加日志输出，或使用Visual Studio附加到游戏进程进行调试。

## 更新日志

### v2.0.0 (2024-12-02)

- ✨ 新增Hook DLL支持
- ✨ 新增Python HookClient
- ✨ 新增PVZInterface统一接口
- ✨ 新增一键启动脚本
- ⚠️ 标记Legacy模式为废弃
- 📚 完善文档和示例

### v1.0.0

- 初始版本（Legacy模式）
