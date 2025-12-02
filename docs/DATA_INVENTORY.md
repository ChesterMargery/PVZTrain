# LLMvsZ 数据清单

本文档列出当前项目用于强化学习训练的所有可用数据，以及尚未实现的数据。

---

## 一、已实现的数据

### 1. 游戏全局状态 (GameState)

| 字段 | 类型 | 说明 |
|------|------|------|
| sun | int | 当前阳光数量 |
| wave | int | 当前波数 (1-indexed) |
| total_waves | int | 总波数 |
| refresh_countdown | int | 下一波刷新倒计时 (cs) |
| huge_wave_countdown | int | 旗帜波倒计时 (cs) |
| game_clock | int | 游戏时钟 (cs) |
| global_clock | int | 全局时钟 |
| initial_countdown | int | 初始刷新倒计时 |
| click_pao_countdown | int | 玉米炮点击冷却 (30cs防误触) |
| zombie_refresh_hp | int | 僵尸刷新血量阈值 |
| scene | int | 场景类型 (0-5) |
| player_level | int | 冒险模式关卡进度 |
| player_coins | int | 金币数量 |
| unlocked_plants | set | 已解锁植物类型集合 |

### 2. 僵尸数据 (ZombieInfo)

| 字段 | 偏移 | 类型 | 说明 |
|------|------|------|------|
| index | - | int | 数组索引 |
| row | 0x1C | int | 所在行 (0-5) |
| x | 0x2C | float | X坐标 (像素) |
| y | 0x30 | float | Y坐标 (像素) |
| type | 0x24 | int | 僵尸类型 (ZombieType枚举) |
| hp | 0xC8 | int | 本体血量 |
| hp_max | 0xCC | int | 本体最大血量 |
| accessory_hp | 0xD0 | int | 防具血量 (路障/铁桶等) |
| state | 0x28 | int | 状态 |
| speed | 0x34 | float | 当前速度 |
| height | 0x38 | float | 高度偏移 (跳跃/飞行) |
| slow_countdown | 0xAC | int | 减速剩余时间 |
| freeze_countdown | 0xB4 | int | 冻结剩余时间 |
| butter_countdown | 0xB0 | int | 黄油剩余时间 |
| at_wave | 0x6C | int | 属于第几波 |
| exist_time | 0x60 | int | 存在时间 |
| state_countdown | 0x68 | int | 状态倒计时 |
| is_eating | 0x51 | bool | 是否在啃食 |
| hurt_width | 0x94 | int | 受伤判定宽度 |
| hurt_height | 0x98 | int | 受伤判定高度 |
| bullet_x | 0x8C | int | 中弹判定X坐标 |
| bullet_y | 0x90 | int | 中弹判定Y坐标 |
| attack_x | 0x9C | int | 攻击判定X坐标 |
| attack_y | 0xA0 | int | 攻击判定Y坐标 |

### 3. 植物数据 (PlantInfo)

| 字段 | 偏移 | 类型 | 说明 |
|------|------|------|------|
| index | - | int | 数组索引 |
| row | 0x1C | int | 所在行 |
| col | 0x28 | int | 所在列 |
| type | 0x24 | int | 植物类型 (PlantType枚举) |
| hp | 0x40 | int | 当前血量 |
| hp_max | 0x44 | int | 最大血量 |
| state | 0x3C | int | 状态 (PlantState枚举) |
| shoot_countdown | 0x90 | int | 发射倒计时 |
| effective | 0x48 | bool | 是否有效/清醒 |
| visible | 0x18 | bool | 是否可见 |
| pumpkin_hp | 0x4C | int | 南瓜血量 |
| cob_countdown | 0x54 | int | 玉米炮装填倒计时 |
| cob_ready | 0x58 | bool | 玉米炮是否就绪 |
| explode_countdown | 0x50 | int | 灰烬/冰菇生效倒计时 |
| blover_countdown | 0x4C | int | 三叶草消失倒计时 |
| mushroom_countdown | 0x130 | int | 蘑菇倒计时 |
| bungee_state | 0x134 | int | 蹦极抓取状态 |
| hurt_width | 0x10 | int | 受伤判定宽度 |
| hurt_height | 0x14 | int | 受伤判定高度 |

### 4. 投射物数据 (ProjectileInfo)

| 字段 | 偏移 | 类型 | 说明 |
|------|------|------|------|
| index | - | int | 数组索引 |
| x | 0x30 | float | X坐标 |
| y | 0x34 | float | Y坐标 |
| row | 0x14 | int | 所在行 |
| type | 0x5C | int | 投射物类型 |
| exist_time | 0x28 | int | 存在时间 |
| is_dead | 0x50 | bool | 是否消失 |
| cob_target_x | 0x38 | float | 玉米炮目标X |
| cob_target_row | 0x18 | int | 玉米炮目标行 |

### 5. 小推车数据 (LawnmowerInfo)

| 字段 | 偏移 | 类型 | 说明 |
|------|------|------|------|
| index | - | int | 数组索引 |
| row | 0x14 | int | 所在行 |
| x | 0x2C | float | X坐标 |
| state | 0x30 | int | 状态 (LawnMowerState枚举) |
| mower_type | 0x34 | int | 类型 (草地/泳池/屋顶) |
| is_dead | 0x48 | bool | 是否消失 |

小推车状态枚举:
- ROLLING_IN = 0 (正在滚入)
- READY = 1 (待命)
- TRIGGERED = 2 (已触发)
- SQUISHED = 3 (被压扁)

### 6. 卡片数据 (SeedInfo)

| 字段 | 偏移 | 类型 | 说明 |
|------|------|------|------|
| index | - | int | 卡槽索引 |
| type | 0x5C | int | 植物类型 |
| recharge_countdown | 0x4C | int | 剩余冷却时间 |
| recharge_time | 0x50 | int | 总冷却时间 |
| usable | 0x70 | bool | 是否可用 |
| imitator_type | 0x60 | int | 模仿者类型 (-1=非模仿者) |

### 7. 场地物品数据 (PlaceItemInfo)

| 字段 | 偏移 | 类型 | 说明 |
|------|------|------|------|
| index | - | int | 数组索引 |
| row | 0x14 | int | 所在行 |
| col | 0x10 | int | 所在列 |
| type | 0x08 | int | 类型 (墓碑/弹坑/梯子等) |
| value | 0x18 | int | 附加值 |
| is_dead | 0x20 | bool | 是否消失 |

### 8. 冰道数据 (ice_trails)

每行一条记录:
| 字段 | 偏移 | 说明 |
|------|------|------|
| row | - | 行号 |
| min_x | 0x60C + row*4 | 冰道起始X坐标 |
| timer | 0x624 + row*4 | 冰道剩余时间 (cs) |

### 9. 场地格子类型 (grid_types)

6x9的二维数组，每个元素是GridSquareType:
- 0 = NONE (无)
- 1 = GRASS (草地)
- 2 = DIRT (泥土/墓碑位)
- 3 = POOL (泳池)
- 4 = HIGH_GROUND (屋顶高台)

### 10. 出怪列表 (spawn_lists)

每波僵尸的类型列表，最多100波，每波最多50个僵尸。

查询方法:
- `get_wave_zombies(wave)` - 返回类型ID列表
- `get_wave_zombies_named(wave)` - 返回类型名称列表
- `get_current_wave_zombies()` - 当前波僵尸
- `get_next_wave_zombies()` - 下一波僵尸
- `get_all_waves_summary()` - 所有波次概览

---

## 二、枚举常量

### 1. ZombieType (33种)

普通僵尸(0)、旗帜(1)、路障(2)、撑杆(3)、铁桶(4)、读报(5)、铁门(6)、橄榄球(7)、舞王(8)、伴舞(9)、鸭子圈(10)、潜水(11)、冰车(12)、雪橇(13)、海豚(14)、小丑(15)、气球(16)、矿工(17)、跳跳(18)、雪人(19)、蹦极(20)、扶梯(21)、投篮(22)、巨人(23)、小鬼(24)、僵王(25)、红眼(32)

### 2. PlantType (48种)

豌豆(0)到忧郁菇(47)的完整列表，包含模仿者(48)。

### 3. ZombiePhase (96种状态)

从PHASE_ZOMBIE_NORMAL到PHASE_SQUASH_DONE_FALLING的完整僵尸状态机。

### 4. PlantState (49种状态)

从STATE_NOTREADY到STATE_LILYPAD_INVULNERABLE的完整植物状态机。

### 5. ProjectileType (14种)

豌豆、冰豌豆、甘蓝、西瓜、冰瓜、火焰豌豆、星星、尖刺、篮球、玉米粒、黄油、玉米炮、灰烬、太阳(向日葵产生)。

---

## 三、尚未实现的数据

### 1. 植物额外状态

| 字段 | 偏移 | 说明 |
|------|------|------|
| is_sleeping | 0x143 | 是否休眠 (白天蘑菇) |
| is_squashed | 0x142 | 是否被压扁 |
| imitater_type | 0x138 | 模仿者原始类型 |

已有偏移定义，但PlantInfo未读取。

### 2. 僵尸额外状态

| 字段 | 偏移 | 说明 |
|------|------|------|
| hypnotized | 0xB8 | 是否被催眠 |
| has_object | 0xBC | 巨人是否持有小鬼 |
| blowing_away | 0xB9 | 是否被吹走 |
| box_exploded | 0xBA | 小丑是否已爆炸 |
| has_balloon | 0xE4 | 气球血量 |
| has_shield | 0xD8 | 盾牌类型 |
| ladder_placed | 0x7C | 扶梯放置位置 |
| target_row | 0x130 | 目标行 (撑杆/矿工等) |
| target_col | 0x80 | 蹦极目标列 |
| accessory_hp_2 | 0xDC | 第二防具血量 (铁门) |
| helm_type | 0xC4 | 头盔类型 |

已有偏移定义，但ZombieInfo未读取。

### 3. 磁铁数据

MagnetItem结构:
- 位置 (x, y)
- 类型 (梯子/铁桶/橄榄球头盔等)
- 目标位置

用于跟踪磁力菇吸走的金属物品。

### 4. 收集物数据

掉落物 (阳光/金币/钻石):
| 字段 | 偏移 | 说明 |
|------|------|------|
| x | 0x24 | X坐标 |
| y | 0x28 | Y坐标 |
| type | 0x58 | 类型 (1银币,2金币,3钻石,4阳光) |
| is_dead | 0x20 | 是否消失 |
| collected | 0x50 | 是否已收集 |
| disappeared | 0x38 | 是否已过期 |

有偏移定义，collect_all_items()中使用，但未作为GameState字段暴露。

### 5. 动画数据

僵尸/植物的动画指针和进度:
- Z_ANIMATION (0x118)
- Z_ANIMATION_PROGRESS (0x58)
- P_ANIMATION (0x94)

可用于精确判断攻击时机。

### 6. 地图物件详细数据

弹坑持续时间、梯子附着的植物等详细信息。

---

## 四、辅助功能

### 1. 动作接口

| 方法 | 说明 |
|------|------|
| plant(row, col, type) | 种植物 |
| shovel(row, col) | 铲植物 |
| collect_all_items() | 收集所有阳光/金币 |

### 2. 查询方法

GameState提供的便捷查询:
- 行分析: get_zombies_in_row, get_plants_in_row, get_row_threat
- 类型查询: get_zombies_by_type, get_plants_by_type
- 状态查询: is_cell_empty, can_plant, has_lawnmower
- 冰道查询: has_ice_trail, is_on_ice
- 格子查询: is_pool, is_roof
- 玉米炮: get_ready_cobs, can_fire_cob, get_flying_cobs

---

## 五、数据来源

- 内存偏移: AsmVsZombies (vector-wlc)
- 枚举/结构: re-plants-vs-zombies (Patoke)
- 游戏版本: PVZ 1.0.0.1051 (原版)

---

## 六、RL训练建议

### 已具备条件
1. 完整的观察空间 (所有实体位置/状态/血量)
2. 基本动作空间 (种植/铲除/收集)
3. 时间信息 (game_clock, 各种countdown)
4. 波次信息 (当前波/总波数/下一波僵尸类型)

### 待开发
1. Gym环境封装 (observation_space, action_space, step, reset)
2. 奖励函数设计 (阳光、击杀、存活时间、关卡完成)
3. 状态向量化 (将GameState转为固定大小的numpy数组)
4. 动作空间细化 (支持玉米炮发射、铲种等高级操作)
