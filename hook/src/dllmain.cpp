#include <Windows.h>
#include "bridge.h"
#include "game.h"

// Hook相关
static BYTE g_originalBytes[5];
static bool g_hooked = false;
static constexpr uintptr_t GAME_LOOP_ADDR = 0x452650;

// 原始游戏循环函数指针
typedef void(__cdecl* GameLoopFunc)();
static GameLoopFunc g_originalGameLoop = nullptr;

// 我们的Hook函数
void __cdecl HookedGameLoop() {
    // 处理Python命令
    Bridge::ProcessCommands();
    
    // 调用原始游戏循环
    if (g_originalGameLoop) {
        g_originalGameLoop();
    }
}

bool InstallHook() {
    if (g_hooked) return true;
    
    // 保存原始字节
    memcpy(g_originalBytes, (void*)GAME_LOOP_ADDR, 5);
    
    // 创建跳转指令 (jmp HookedGameLoop)
    DWORD oldProtect;
    VirtualProtect((void*)GAME_LOOP_ADDR, 5, PAGE_EXECUTE_READWRITE, &oldProtect);
    
    // 计算相对偏移
    uintptr_t hookAddr = (uintptr_t)HookedGameLoop;
    int relativeOffset = hookAddr - GAME_LOOP_ADDR - 5;
    
    // 写入跳转指令
    BYTE jumpCode[5] = {
        0xE9,  // jmp
        (BYTE)(relativeOffset & 0xFF),
        (BYTE)((relativeOffset >> 8) & 0xFF),
        (BYTE)((relativeOffset >> 16) & 0xFF),
        (BYTE)((relativeOffset >> 24) & 0xFF)
    };
    
    memcpy((void*)GAME_LOOP_ADDR, jumpCode, 5);
    VirtualProtect((void*)GAME_LOOP_ADDR, 5, oldProtect, &oldProtect);
    
    g_hooked = true;
    return true;
}

void UninstallHook() {
    if (!g_hooked) return;
    
    // 恢复原始字节
    DWORD oldProtect;
    VirtualProtect((void*)GAME_LOOP_ADDR, 5, PAGE_EXECUTE_READWRITE, &oldProtect);
    memcpy((void*)GAME_LOOP_ADDR, g_originalBytes, 5);
    VirtualProtect((void*)GAME_LOOP_ADDR, 5, oldProtect, &oldProtect);
    
    g_hooked = false;
}

BOOL APIENTRY DllMain(HMODULE hModule, DWORD dwReason, LPVOID lpReserved) {
    switch (dwReason) {
    case DLL_PROCESS_ATTACH:
        // DLL被加载
        DisableThreadLibraryCalls(hModule);
        
        // 初始化TCP服务器
        if (Bridge::Initialize(12345)) {
            // 安装Hook
            InstallHook();
        }
        break;
        
    case DLL_PROCESS_DETACH:
        // DLL被卸载
        UninstallHook();
        Bridge::Shutdown();
        break;
    }
    return TRUE;
}
