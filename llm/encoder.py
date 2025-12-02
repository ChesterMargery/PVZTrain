"""
State Encoder

Encodes GameState into YAML format for LLM consumption.
"""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass

from game.state import GameState, SeedInfo
from game.zombie import ZombieInfo
from game.plant import PlantInfo
from game.projectile import ProjectileInfo
from data.plants import PlantType, PLANT_COST, ATTACKING_PLANTS
from data.zombies import ZombieType, get_zombie_total_hp
from data.offsets import SceneType


# Plant names mapping
PLANT_NAMES = {
    PlantType.PEASHOOTER: "豌豆",
    PlantType.SUNFLOWER: "向日葵",
    PlantType.CHERRY_BOMB: "樱桃",
    PlantType.WALLNUT: "坚果",
    PlantType.POTATO_MINE: "土豆雷",
    PlantType.SNOW_PEA: "寒冰",
    PlantType.CHOMPER: "食人花",
    PlantType.REPEATER: "双发",
    PlantType.PUFFSHROOM: "小喷菇",
    PlantType.SUNSHROOM: "阳光菇",
    PlantType.FUMESHROOM: "大喷菇",
    PlantType.GRAVEBUSTER: "墓碑吞噬者",
    PlantType.HYPNOSHROOM: "魅惑菇",
    PlantType.SCAREDYSHROOM: "胆小菇",
    PlantType.ICESHROOM: "寒冰菇",
    PlantType.DOOMSHROOM: "毁灭菇",
    PlantType.LILYPAD: "睡莲",
    PlantType.SQUASH: "倭瓜",
    PlantType.THREEPEATER: "三线",
    PlantType.TANGLEKELP: "缠绕海草",
    PlantType.JALAPENO: "辣椒",
    PlantType.SPIKEWEED: "地刺",
    PlantType.TORCHWOOD: "火炬",
    PlantType.TALLNUT: "高坚果",
    PlantType.SEASHROOM: "海蘑菇",
    PlantType.PLANTERN: "路灯花",
    PlantType.CACTUS: "仙人掌",
    PlantType.BLOVER: "三叶草",
    PlantType.SPLITPEA: "裂荚",
    PlantType.STARFRUIT: "杨桃",
    PlantType.PUMPKIN: "南瓜头",
    PlantType.MAGNETSHROOM: "磁力菇",
    PlantType.CABBAGEPULT: "卷心菜",
    PlantType.FLOWERPOT: "花盆",
    PlantType.KERNELPULT: "玉米投手",
    PlantType.COFFEEBEAN: "咖啡豆",
    PlantType.GARLIC: "大蒜",
    PlantType.UMBRELLALEAF: "叶子伞",
    PlantType.MARIGOLD: "金盏花",
    PlantType.MELONPULT: "西瓜投手",
    PlantType.GATLINGPEA: "加特林",
    PlantType.TWINSUNFLOWER: "双子向日葵",
    PlantType.GLOOMSHROOM: "忧郁菇",
    PlantType.CATTAIL: "香蒲",
    PlantType.WINTERMELON: "冰瓜",
    PlantType.GOLDMAGNET: "吸金磁",
    PlantType.SPIKEROCK: "地刺王",
    PlantType.COBCANNON: "玉米炮",
    PlantType.IMITATER: "模仿者",
}

# Zombie names mapping
ZOMBIE_NAMES = {
    ZombieType.ZOMBIE: "普通",
    ZombieType.FLAG: "旗帜",
    ZombieType.CONEHEAD: "路障",
    ZombieType.POLEVAULTER: "撑杆",
    ZombieType.BUCKETHEAD: "铁桶",
    ZombieType.NEWSPAPER: "读报",
    ZombieType.SCREENDOOR: "铁门",
    ZombieType.FOOTBALL: "橄榄球",
    ZombieType.DANCING: "舞王",
    ZombieType.BACKUP: "伴舞",
    ZombieType.DUCKYTUBE: "鸭子",
    ZombieType.SNORKEL: "潜水",
    ZombieType.ZOMBONI: "冰车",
    ZombieType.BOBSLED: "雪橇",
    ZombieType.DOLPHIN: "海豚",
    ZombieType.JACKINBOX: "小丑",
    ZombieType.BALLOON: "气球",
    ZombieType.DIGGER: "矿工",
    ZombieType.POGO: "跳跳",
    ZombieType.YETI: "雪人",
    ZombieType.BUNGEE: "蹦极",
    ZombieType.LADDER: "扶梯",
    ZombieType.CATAPULT: "投篮",
    ZombieType.GARGANTUAR: "巨人",
    ZombieType.IMP: "小鬼",
    ZombieType.ZOMBOSS: "僵王",
    ZombieType.GIGA_GARGANTUAR: "红眼",
}


@dataclass
class RowAnalysis:
    """Analysis data for a row"""
    row: int
    attacker_count: int
    defender_count: int
    zombie_count: int
    closest_zombie_x: float
    threat: float
    dps: float
    incoming_hp: int


@dataclass
class EmergencyEvent:
    """Emergency event data"""
    event_type: str
    row: int
    data: Dict[str, Any]


class StateEncoder:
    """Encodes GameState to YAML format for LLM"""
    
    def __init__(self):
        self.action_history: List[Dict[str, Any]] = []
    
    def encode(self, state: GameState) -> str:
        """
        Encode GameState to YAML format string.
        
        Args:
            state: Current game state
            
        Returns:
            YAML formatted string for LLM input
        """
        lines = []
        
        # Global state with sun budget warning
        sun_warning = ""
        if state.sun < 50:
            sun_warning = " ⚠️危险:无法种任何植物"
        elif state.sun < 100:
            sun_warning = " ⚠️低阳光:只能种向日葵/坚果"
        elif state.sun < 150:
            sun_warning = " 注意:无法使用樱桃/辣椒"
        
        lines.append("# ===== 全局状态 =====")
        lines.append("G:")
        lines.append(f"  wave: {state.wave}/{state.total_waves}")
        lines.append(f"  sun: {state.sun}{sun_warning}")
        
        # Calculate affordable actions
        affordable = []
        for seed in state.seeds:
            if seed.type >= 0 and seed.usable:
                cost = PLANT_COST.get(seed.type, 100)
                if cost <= state.sun:
                    name = PLANT_NAMES.get(seed.type, f"t{seed.type}")
                    affordable.append(f"{name}({cost})")
        if affordable:
            lines.append(f"  affordable: [{', '.join(affordable)}]")
        else:
            lines.append(f"  affordable: [] # 无可用植物!")
        
        lines.append(f"  scene: {state.scene}")
        lines.append(f"  clock: {state.game_clock}")
        lines.append(f"  refresh_cd: {state.refresh_countdown}")
        lines.append(f"  huge_wave_cd: {state.huge_wave_countdown}")
        lines.append(f"  player_level: {state.player_level}")
        lines.append(f"  coins: {state.player_coins}")
        lines.append("")
        
        # Player inventory (unlocked plants)
        lines.append("# ===== 仓库 (已解锁植物) =====")
        lines.append("# 注意: 这是玩家解锁的所有植物，不是当前卡槽")
        lines.append("I:")
        if state.unlocked_plants:
            unlocked_list = sorted(list(state.unlocked_plants), key=lambda x: x)
            unlocked_names = [PLANT_NAMES.get(pt, f"植物{pt}") for pt in unlocked_list]
            lines.append(f"  count: {len(unlocked_list)}")
            lines.append(f"  plants: [{', '.join(unlocked_names)}]")
        else:
            lines.append("  count: 0")
            lines.append("  plants: []")
        lines.append("")
        
        # Seeds (card slots) - THIS IS THE ONLY SOURCE OF AVAILABLE PLANTS!
        lines.append("# ===== 卡槽 (可用植物) =====")
        lines.append("# ⚠️ 只能使用以下卡片中的植物!")
        lines.append("S:")
        for seed in state.seeds:
            if seed.type >= 0:
                name = PLANT_NAMES.get(seed.type, f"植物{seed.type}")
                cost = PLANT_COST.get(seed.type, 100)
                cd_pct = int(seed.cooldown_percent)
                can_use = "✓可用" if seed.usable and cost <= state.sun else "✗"
                lines.append(f"  - {{i: {seed.index}, t: {seed.type}, n: \"{name}\", "
                           f"cost: {cost}, ready: {str(seed.usable).lower()}, cd: {cd_pct}}} {can_use}")
        lines.append("")
        
        # Plants
        lines.append("# ===== 植物 =====")
        lines.append("P:")
        for plant in state.alive_plants:
            name = PLANT_NAMES.get(plant.type, f"植物{plant.type}")
            hp_str = f"{plant.hp}/{plant.hp_max}"
            
            plant_line = f"  - {{r: {plant.row}, c: {plant.col}, t: {plant.type}, hp: {hp_str}, atk_cd: {plant.shoot_countdown}"
            
            # Add cob cannon specific fields
            if plant.type == PlantType.COBCANNON:
                plant_line += f", cob_cd: {plant.cob_countdown}, cob_ready: {str(plant.cob_ready).lower()}"
            
            plant_line += "}"
            
            # Add warning for low HP defensive plants
            if plant.hp_ratio < 0.4 and plant.is_defender:
                plant_line += "  # ⚠️"
            
            lines.append(plant_line)
        lines.append("")
        
        # Zombies
        lines.append("# ===== 僵尸 =====")
        lines.append("Z:")
        for zombie in state.alive_zombies:
            name = ZOMBIE_NAMES.get(zombie.type, f"僵尸{zombie.type}")
            hp_str = f"{zombie.total_hp}/{get_zombie_total_hp(zombie.type)}"
            eta = int(zombie.time_to_reach(0)) if zombie.effective_speed > 0 else 9999
            
            # Predict position based on latency (compensate for ~2s delay)
            # This helps the LLM place plants in front of moving zombies
            predicted_x = zombie.position_at(200)
            
            zombie_line = (f"  - {{r: {zombie.row}, x: {int(predicted_x)}, t: {zombie.type}, "
                          f"n: \"{name}\", hp: {hp_str}, spd: {zombie.effective_speed:.2f}, "
                          f"slow: {zombie.slow_countdown}, freeze: {zombie.freeze_countdown}")
            
            if eta < 9999:
                zombie_line += f", eta: {eta}"
            
            zombie_line += "}"
            lines.append(zombie_line)
        lines.append("")
        
        # Projectiles
        lines.append("# ===== 子弹 (场上投射物) =====")
        lines.append("B:")
        for proj in state.projectiles:
            if proj.is_dead:
                continue
            proj_line = f"  - {{r: {proj.row}, x: {int(proj.x)}, t: {proj.type}"
            
            if proj.is_cob:
                proj_line += f", target_x: {int(proj.actual_cob_target_x)}, target_r: {proj.cob_target_row}"
            
            proj_line += "}"
            lines.append(proj_line)
        lines.append("")
        
        # Lawnmowers - scene-aware row count
        row_count = SceneType.get_row_count(state.scene)
        lines.append("# ===== 小推车 =====")
        lawnmower_status = [str(state.has_lawnmower(r)).lower() for r in range(row_count)]
        lines.append(f"L: [{', '.join(lawnmower_status)}]")
        lines.append("")
        
        # Row analysis - scene-aware row count
        lines.append("# ===== 行分析 =====")
        lines.append("R:")
        for row in range(row_count):
            analysis = self._analyze_row(state, row)
            warning = "  # ⚠️高威胁" if analysis.threat > 5.0 else ""
            lines.append(f"  - {{r: {row}, atk: {analysis.attacker_count}, "
                        f"def: {analysis.defender_count}, z_cnt: {analysis.zombie_count}, "
                        f"z_closest: {int(analysis.closest_zombie_x)}, threat: {analysis.threat:.1f}}}{warning}")
        lines.append("")
        
        # DPS estimation
        lines.append("# ===== DPS估算 =====")
        lines.append("D:")
        for row in range(row_count):
            analysis = self._analyze_row(state, row)
            warning = "  # ⚠️" if analysis.dps == 0 and analysis.incoming_hp > 0 else ""
            lines.append(f"  - {{r: {row}, dps: {analysis.dps:.1f}, incoming: {analysis.incoming_hp}}}{warning}")
        lines.append("")
        
        # Action history
        if self.action_history:
            lines.append("# ===== 历史动作 =====")
            lines.append("H:")
            for action in self.action_history[-10:]:
                lines.append(f"  - {action}")
            lines.append("")
        
        # Emergency events
        emergencies = self._detect_emergencies(state)
        if emergencies:
            lines.append("# ===== 紧急事件 =====")
            lines.append("E:")
            for event in emergencies:
                lines.append(f"  - {event}")
            lines.append("")
        
        return "\n".join(lines)
    
    def _analyze_row(self, state: GameState, row: int) -> RowAnalysis:
        """Analyze a single row"""
        # Count attackers and defenders
        row_plants = state.get_plants_in_row(row)
        attacker_count = sum(1 for p in row_plants if p.type in ATTACKING_PLANTS)
        defender_count = state.get_row_defense_count(row)
        
        # Get zombie info
        row_zombies = state.get_zombies_in_row(row)
        zombie_count = len(row_zombies)
        closest = state.get_closest_zombie_in_row(row)
        closest_x = closest.x if closest else 800.0
        
        # Calculate threat
        threat = state.get_row_threat(row)
        
        # Calculate DPS
        dps = sum(p.attack_value for p in row_plants)
        
        # Calculate incoming HP
        incoming_hp = sum(z.total_hp for z in row_zombies)
        
        return RowAnalysis(
            row=row,
            attacker_count=attacker_count,
            defender_count=defender_count,
            zombie_count=zombie_count,
            closest_zombie_x=closest_x,
            threat=threat,
            dps=dps,
            incoming_hp=incoming_hp
        )
    
    def _detect_emergencies(self, state: GameState) -> List[Dict[str, Any]]:
        """Detect emergency events"""
        emergencies = []
        row_count = SceneType.get_row_count(state.scene)
        
        for row in range(row_count):
            row_zombies = state.get_zombies_in_row(row)
            
            for zombie in row_zombies:
                # Zombie close to home
                if zombie.x < 200:
                    name = ZOMBIE_NAMES.get(zombie.type, f"僵尸{zombie.type}")
                    eta = int(zombie.time_to_reach(0)) if zombie.effective_speed > 0 else 9999
                    emergencies.append({
                        "type": "zombie_close",
                        "r": row,
                        "x": int(zombie.x),
                        "name": name,
                        "eta": eta
                    })
            
            # Check for low HP defensive plants
            for plant in state.get_plants_in_row(row):
                if plant.is_defender and plant.hp_ratio < 0.4:
                    name = PLANT_NAMES.get(plant.type, f"植物{plant.type}")
                    emergencies.append({
                        "type": "plant_low_hp",
                        "r": row,
                        "c": plant.col,
                        "name": name,
                        "hp_pct": int(plant.hp_ratio * 100)
                    })
            
            # Check for no attacker in row with zombies
            if row_zombies and state.get_row_attacker_count(row) == 0:
                emergencies.append({
                    "type": "no_attacker",
                    "r": row
                })
            
            # Check for lost lawnmower
            if not state.has_lawnmower(row) and row_zombies:
                emergencies.append({
                    "type": "lawnmower_lost",
                    "r": row
                })
        
        return emergencies
    
    def add_action_to_history(self, clock: int, action_type: str, 
                              plant_type: Optional[int] = None,
                              row: Optional[int] = None,
                              col: Optional[int] = None,
                              success: bool = True,
                              error: Optional[str] = None) -> None:
        """Add action to history"""
        action_record = {
            "t": clock,
            "a": action_type
        }
        
        if plant_type is not None:
            action_record["type"] = plant_type
        if row is not None:
            action_record["r"] = row
        if col is not None:
            action_record["c"] = col
        
        action_record["ok"] = success
        
        if error:
            action_record["err"] = error
        
        self.action_history.append(action_record)
        
        # Keep only recent history
        if len(self.action_history) > 20:
            self.action_history = self.action_history[-20:]
