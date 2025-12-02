@echo off
echo Building PVZ Hook DLL...
echo.

REM 创建build目录
if not exist build mkdir build
cd build

REM 配置CMake (32位)
echo Configuring CMake...
cmake -G "Visual Studio 17 2022" -A Win32 ..
if %ERRORLEVEL% NEQ 0 (
    echo CMake configuration failed!
    pause
    exit /b 1
)

REM 构建Release版本
echo Building Release...
cmake --build . --config Release
if %ERRORLEVEL% NEQ 0 (
    echo Build failed!
    pause
    exit /b 1
)

REM 复制DLL到上层目录
echo Copying DLL...
copy Release\pvz_hook.dll ..
if %ERRORLEVEL% NEQ 0 (
    echo Failed to copy DLL!
    pause
    exit /b 1
)

cd ..
echo.
echo Build successful! pvz_hook.dll is ready.
pause
