#pragma once

#include <cstdint>

// PVZ游戏函数接口
// 基于 AsmVsZombies (AVZ) 实现

namespace PVZ {

// 基础地址读取
uintptr_t GetBase();
uintptr_t GetBoard();
uintptr_t GetGameUI();

// 游戏状态读取
int GetSun();
int GetWave();
int GetScene();
bool IsInGame();
bool IsZombieInHouse();  // 检测是否有僵尸进屋（失败）

// 游戏操作函数
bool PutPlant(int row, int col, int type);  // 种植物
bool Shovel(int row, int col);              // 铲植物
bool FireCob(int x, int y);                 // 发射玉米炮
bool ChooseCard(int type);                  // 选卡
bool Rock();                                // 开始游戏（点击Let's Rock）
bool MakeNewBoard();                        // 重置关卡
bool EnterGame(int mode);                   // 进入游戏模式
bool BackToMain();                          // 返回主菜单

}  // namespace PVZ
