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
    
    // 读取更多状态信息
    uintptr_t board = PVZ::GetBoard();
    if (board) {
        // 读取总波数
        info.total_waves = *(int*)(board + 0x5564);
        // 读取游戏时钟
        info.game_clock = *(int*)(board + 0x5568);
        
        // 统计植物和僵尸数量
        uintptr_t plantArray = *(uintptr_t*)(board + 0xAC);
        int plantMax = *(int*)(board + 0xB0);
        info.plant_count = 0;
        if (plantArray && plantMax > 0 && plantMax <= 200) {
            for (int i = 0; i < plantMax; i++) {
                uintptr_t addr = plantArray + i * 0x14C;
                bool dead = *(bool*)(addr + 0x141);
                if (!dead) info.plant_count++;
            }
        }
        
        uintptr_t zombieArray = *(uintptr_t*)(board + 0x90);
        int zombieMax = *(int*)(board + 0x94);
        info.zombie_count = 0;
        if (zombieArray && zombieMax > 0 && zombieMax <= 200) {
            for (int i = 0; i < zombieMax; i++) {
                uintptr_t addr = zombieArray + i * 0x15C;
                bool dead = *(bool*)(addr + 0xEC);
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
