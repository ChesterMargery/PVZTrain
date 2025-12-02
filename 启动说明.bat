@echo off
chcp 65001 >nul
echo ========================================
echo    PVZTrain 使用说明
echo ========================================
echo.
echo 【快速开始】
echo.
echo 1. 安装Python 3.7或更高版本
echo    下载地址: https://www.python.org/downloads/
echo.
echo 2. 确保游戏版本为 PVZ 1.0.0.1051（中文年度版）
echo.
echo 3. 运行方式：
echo    方式一：双击"一键启动.bat"（推荐）
echo    方式二：手动运行 python examples/hook_example.py
echo.
echo 【目录说明】
echo.
echo pvz_hook.dll       - Hook DLL（预编译）
echo core/              - Python核心接口
echo hook_client/       - Hook客户端
echo memory/            - 内存读写模块
echo game/              - 游戏状态
echo data/              - 数据定义
echo engine/            - 引擎
echo utils/             - 工具函数
echo tools/             - 工具脚本
echo examples/          - 示例代码
echo main.py            - 主入口
echo config.py          - 配置
echo requirements.txt   - Python依赖
echo README.md          - 详细文档
echo LICENSE            - 许可证
echo HOOK_MIGRATION.md  - 迁移指南
echo.
echo 【使用说明】
echo.
echo 1. 启动游戏《植物大战僵尸》
echo 2. 进入或不进入关卡都可以
echo 3. 运行"一键启动.bat"
echo 4. 程序会自动注入DLL并开始执行
echo.
echo 【常见问题】
echo.
echo Q: DLL注入失败？
echo A: 确保游戏已运行，使用管理员权限启动脚本
echo.
echo Q: 连接失败？
echo A: 等待2-3秒让DLL初始化，或重启游戏
echo.
echo Q: 游戏崩溃？
echo A: 确认游戏版本为1.0.0.1051，关闭其他修改器
echo.
echo 【更多信息】
echo.
echo 详细文档请查看 README.md
echo 问题反馈: https://github.com/ChesterMargery/PVZTrain/issues
echo.
echo ========================================
pause
