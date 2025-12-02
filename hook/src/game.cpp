#include "game.h"
#include <Windows.h>

// PVZ游戏内存地址（参考AVZ）
namespace Addr {
    constexpr uintptr_t BASE = 0x6A9EC0;
    constexpr uintptr_t MAIN_OBJECT = 0x768;
    constexpr uintptr_t GAME_UI = 0x7FC;
    constexpr uintptr_t SUN = 0x5560;
    constexpr uintptr_t WAVE = 0x557C;
    constexpr uintptr_t SCENE = 0x554C;
    
    // 函数地址
    constexpr uintptr_t FUNC_PUT_PLANT = 0x40D120;
    constexpr uintptr_t FUNC_SHOVEL = 0x411060;
    constexpr uintptr_t FUNC_CHOOSE_CARD = 0x486030;
    constexpr uintptr_t FUNC_ROCK = 0x486D20;
    constexpr uintptr_t FUNC_MAKE_NEW_BOARD = 0x44F5F0;
    constexpr uintptr_t FUNC_ENTER_GAME = 0x44F560;
    constexpr uintptr_t FUNC_BACK_TO_MAIN = 0x44FEB0;
    
    // 偏移量
    constexpr uintptr_t PLANT_ARRAY = 0xAC;
    constexpr uintptr_t PLANT_COUNT_MAX = 0xB0;
    constexpr uintptr_t PLANT_SIZE = 0x14C;
    constexpr uintptr_t P_ROW = 0x1C;
    constexpr uintptr_t P_COL = 0x28;
    constexpr uintptr_t P_DEAD = 0x141;
    constexpr uintptr_t SEED_CHOOSER = 0x774;
}

namespace PVZ {

uintptr_t GetBase() {
    return *(uintptr_t*)Addr::BASE;
}

uintptr_t GetBoard() {
    uintptr_t base = GetBase();
    if (!base) return 0;
    return *(uintptr_t*)(base + Addr::MAIN_OBJECT);
}

uintptr_t GetGameUI() {
    uintptr_t base = GetBase();
    if (!base) return 0;
    return *(uintptr_t*)(base + Addr::GAME_UI);
}

int GetSun() {
    uintptr_t board = GetBoard();
    if (!board) return 0;
    return *(int*)(board + Addr::SUN);
}

int GetWave() {
    uintptr_t board = GetBoard();
    if (!board) return 0;
    return *(int*)(board + Addr::WAVE);
}

int GetScene() {
    uintptr_t board = GetBoard();
    if (!board) return 0;
    return *(int*)(board + Addr::SCENE);
}

bool IsInGame() {
    uintptr_t ui = GetGameUI();
    return ui == 3;
}

bool IsZombieInHouse() {
    // 检测小车是否被触发或有僵尸到达最左侧
    // 简化版本：检测是否有僵尸X坐标 < 50
    uintptr_t board = GetBoard();
    if (!board) return false;
    
    // 读取僵尸数组（这里简化，实际需要遍历检查）
    // 如果有僵尸进屋，游戏会触发失败
    return false;  // TODO: 完整实现
}

bool PutPlant(int row, int col, int type) {
    uintptr_t board = GetBoard();
    if (!board) return false;
    
    // 调用游戏函数 Board::AddPlant
    // 参考AVZ实现
    typedef void(__thiscall* AddPlantFunc)(uintptr_t board, int col, int row, int type, int imitatorType);
    AddPlantFunc addPlant = (AddPlantFunc)Addr::FUNC_PUT_PLANT;
    
    __asm {
        push -1                 // imitatorType
        push type               // plant type
        mov eax, row            // row (通过eax传递)
        push col                // col
        mov ecx, board          // this pointer
        call addPlant
    }
    
    return true;
}

bool Shovel(int row, int col) {
    uintptr_t board = GetBoard();
    if (!board) return false;
    
    // 查找该位置的植物
    uintptr_t plantArray = *(uintptr_t*)(board + Addr::PLANT_ARRAY);
    int plantMax = *(int*)(board + Addr::PLANT_COUNT_MAX);
    
    if (!plantArray || plantMax <= 0) return false;
    if (plantMax > 200) plantMax = 200;  // 安全限制
    
    uintptr_t plantAddr = 0;
    for (int i = 0; i < plantMax; i++) {
        uintptr_t addr = plantArray + i * Addr::PLANT_SIZE;
        if (*(bool*)(addr + Addr::P_DEAD)) continue;
        
        int pRow = *(int*)(addr + Addr::P_ROW);
        int pCol = *(int*)(addr + Addr::P_COL);
        
        if (pRow == row && pCol == col) {
            plantAddr = addr;
            break;
        }
    }
    
    if (!plantAddr) return false;
    
    // 调用铲除函数
    typedef void(__cdecl* RemovePlantFunc)(uintptr_t plant);
    RemovePlantFunc removePlant = (RemovePlantFunc)Addr::FUNC_SHOVEL;
    removePlant(plantAddr);
    
    return true;
}

bool FireCob(int x, int y) {
    // 发射玉米炮需要找到炮的地址，然后调用发射函数
    // 简化版本，实际需要更复杂的逻辑
    return false;  // TODO: 完整实现
}

bool ChooseCard(int type) {
    uintptr_t base = GetBase();
    if (!base) return false;
    
    uintptr_t gameUI = GetGameUI();
    if (gameUI != 2) return false;  // 必须在选卡界面
    
    uintptr_t seedChooser = *(uintptr_t*)(base + Addr::SEED_CHOOSER);
    if (!seedChooser) return false;
    
    // 计算卡片地址：cardType * 60 + 0xa4 + seedChooser
    uintptr_t cardAddr = type * 60 + 0xa4 + seedChooser;
    
    // 调用选卡函数
    typedef void(__cdecl* ChooseCardFunc)(uintptr_t cardAddr);
    ChooseCardFunc chooseCard = (ChooseCardFunc)Addr::FUNC_CHOOSE_CARD;
    chooseCard(cardAddr);
    
    return true;
}

bool Rock() {
    uintptr_t base = GetBase();
    if (!base) return false;
    
    uintptr_t gameUI = GetGameUI();
    if (gameUI != 2) return false;
    
    uintptr_t seedChooser = *(uintptr_t*)(base + Addr::SEED_CHOOSER);
    if (!seedChooser) return false;
    
    // 调用Rock函数
    typedef void(__cdecl* RockFunc)();
    RockFunc rock = (RockFunc)Addr::FUNC_ROCK;
    
    __asm {
        mov ebx, seedChooser
        mov esi, base
        mov edi, 1
        mov ebp, 1
        call rock
    }
    
    return true;
}

bool MakeNewBoard() {
    uintptr_t base = GetBase();
    if (!base) return false;
    
    // 调用MakeNewBoard函数
    typedef void(__thiscall* MakeNewBoardFunc)(uintptr_t base);
    MakeNewBoardFunc makeNewBoard = (MakeNewBoardFunc)Addr::FUNC_MAKE_NEW_BOARD;
    
    __asm {
        mov ecx, base
        call makeNewBoard
    }
    
    return true;
}

bool EnterGame(int mode) {
    uintptr_t base = GetBase();
    if (!base) return false;
    
    // 调用EnterGame函数
    typedef void(__cdecl* EnterGameFunc)(int mode, int ok);
    EnterGameFunc enterGame = (EnterGameFunc)Addr::FUNC_ENTER_GAME;
    
    __asm {
        push 1          // ok = true
        push mode       // game mode
        mov esi, base
        call enterGame
    }
    
    return true;
}

bool BackToMain() {
    uintptr_t base = GetBase();
    if (!base) return false;
    
    uintptr_t gameUI = GetGameUI();
    if (gameUI != 3) return false;
    
    // 调用BackToMain函数
    typedef void(__thiscall* BackToMainFunc)(uintptr_t base);
    BackToMainFunc backToMain = (BackToMainFunc)Addr::FUNC_BACK_TO_MAIN;
    
    __asm {
        mov eax, base
        mov ecx, backToMain
        call ecx
    }
    
    return true;
}

}  // namespace PVZ
