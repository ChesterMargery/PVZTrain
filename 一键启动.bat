@echo off
chcp 65001 >nul
echo ========================================
echo    PVZTrain 一键启动脚本
echo ========================================
echo.

REM 检查Python是否安装
python --version >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [错误] 未检测到Python！
    echo 请先安装Python 3.7或更高版本
    echo 下载地址: https://www.python.org/downloads/
    echo.
    pause
    exit /b 1
)

echo [1/4] 检查Python版本...
python --version

echo [2/4] 安装依赖包...
pip install -r requirements.txt
if %ERRORLEVEL% NEQ 0 (
    echo [错误] 依赖安装失败！
    pause
    exit /b 1
)

echo [3/4] 检查DLL文件...
if not exist "pvz_hook.dll" (
    echo [错误] 未找到 pvz_hook.dll！
    echo 请确保DLL文件在当前目录
    pause
    exit /b 1
)

echo [4/4] 启动程序...
echo.
echo ========================================
echo 请先启动游戏《植物大战僵尸》
echo 然后按任意键继续...
echo ========================================
pause >nul

echo.
echo 正在运行示例程序...
python examples/hook_example.py

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [错误] 程序执行失败！
    pause
    exit /b 1
)

echo.
echo 程序执行完成！
pause
