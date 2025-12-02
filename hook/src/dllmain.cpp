#include <Windows.h>
#include "bridge.h"
#include "game.h"

// Hook相关 - 采用AVZ的虚函数表Hook方式
static bool g_hooked = false;
static constexpr uintptr_t VTABLE_ADDR = 0x667bc0;  // 虚函数表地址
static constexpr uintptr_t ORIGINAL_FUNC = 0x452650;  // 原始游戏循环函数地址
static uint32_t g_originalVtableEntry = 0;  // 保存原始虚函数表项

// 我们的Hook函数
void __cdecl HookedGameLoop() {
    // 处理Python命令
    Bridge::ProcessCommands();
    
    // 直接调用原始函数地址
    typedef void(__cdecl* GameLoopFunc)();
    ((GameLoopFunc)ORIGINAL_FUNC)();
}

bool InstallHook() {
    if (g_hooked) return true;
    
    // 修改虚函数表指针
    DWORD oldProtect;
    if (!VirtualProtect((void*)0x400000, 0x35E000, PAGE_EXECUTE_READWRITE, &oldProtect)) {
        return false;
    }
    
    // 保存原始虚函数表项
    g_originalVtableEntry = *(uint32_t*)VTABLE_ADDR;
    
    // 替换为我们的Hook函数
    *(uint32_t*)VTABLE_ADDR = (uint32_t)&HookedGameLoop;
    
    // 刷新指令缓存
    FlushInstructionCache(GetCurrentProcess(), (void*)VTABLE_ADDR, sizeof(uint32_t));
    
    VirtualProtect((void*)0x400000, 0x35E000, oldProtect, &oldProtect);
    
    g_hooked = true;
    return true;
}

void UninstallHook() {
    if (!g_hooked) return;
    
    // 恢复原始虚函数表项
    DWORD oldProtect;
    if (!VirtualProtect((void*)0x400000, 0x35E000, PAGE_EXECUTE_READWRITE, &oldProtect)) {
        return;
    }
    
    *(uint32_t*)VTABLE_ADDR = g_originalVtableEntry;
    
    // 刷新指令缓存
    FlushInstructionCache(GetCurrentProcess(), (void*)VTABLE_ADDR, sizeof(uint32_t));
    
    VirtualProtect((void*)0x400000, 0x35E000, oldProtect, &oldProtect);
    
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
