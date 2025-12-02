#include "state.h"
#include "game.h"
#include <sstream>
#include <iomanip>

namespace State {

std::string GetGameState() {
    GameStateInfo info = {};
    
    info.sun = PVZ::GetSun();
    info.wave = PVZ::GetWave();
    info.scene = PVZ::GetScene();
    info.in_game = PVZ::IsInGame();
    
    // Offsets (from game.cpp Addr namespace)
    constexpr uintptr_t TOTAL_WAVE = 0x5564;
    constexpr uintptr_t GAME_CLOCK = 0x5568;
    constexpr uintptr_t PLANT_ARRAY = 0xAC;
    constexpr uintptr_t PLANT_COUNT_MAX = 0xB0;
    constexpr uintptr_t PLANT_SIZE = 0x14C;
    constexpr uintptr_t P_DEAD = 0x141;
    constexpr uintptr_t ZOMBIE_ARRAY = 0x90;
    constexpr uintptr_t ZOMBIE_COUNT_MAX = 0x94;
    constexpr uintptr_t ZOMBIE_SIZE = 0x15C;
    constexpr uintptr_t Z_DEAD = 0xEC;
    
    // 读取更多状态信息
    uintptr_t board = PVZ::GetBoard();
    if (board) {
        // 读取总波数
        info.total_waves = *(int*)(board + TOTAL_WAVE);
        // 读取游戏时钟
        info.game_clock = *(int*)(board + GAME_CLOCK);
        
        // 统计植物和僵尸数量
        uintptr_t plantArray = *(uintptr_t*)(board + PLANT_ARRAY);
        int plantMax = *(int*)(board + PLANT_COUNT_MAX);
        info.plant_count = 0;
        if (plantArray && plantMax > 0 && plantMax <= 200) {
            for (int i = 0; i < plantMax; i++) {
                uintptr_t addr = plantArray + i * PLANT_SIZE;
                bool dead = *(bool*)(addr + P_DEAD);
                if (!dead) info.plant_count++;
            }
        }
        
        uintptr_t zombieArray = *(uintptr_t*)(board + ZOMBIE_ARRAY);
        int zombieMax = *(int*)(board + ZOMBIE_COUNT_MAX);
        info.zombie_count = 0;
        if (zombieArray && zombieMax > 0 && zombieMax <= 200) {
            for (int i = 0; i < zombieMax; i++) {
                uintptr_t addr = zombieArray + i * ZOMBIE_SIZE;
                // 僵尸死亡标志通常在 0xEC 偏移处
                // 注意：某些僵尸状态可能需要检查多个标志位
                bool dead = *(bool*)(addr + Z_DEAD);
                if (!dead) info.zombie_count++;
            }
        }
    }
    
    // 构建简单的JSON格式字符串
    std::ostringstream oss;
    oss << "{"
        << "\"sun\":" << info.sun << ","
        << "\"wave\":" << info.wave << ","
        << "\"total_waves\":" << info.total_waves << ","
        << "\"scene\":" << info.scene << ","
        << "\"game_clock\":" << info.game_clock << ","
        << "\"in_game\":" << (info.in_game ? "true" : "false") << ","
        << "\"zombie_count\":" << info.zombie_count << ","
        << "\"plant_count\":" << info.plant_count
        << "}";
    
    return oss.str();
}

}  // namespace State
