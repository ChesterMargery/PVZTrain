#!/usr/bin/env python3
"""
PVZ Memory Interface

Memory interface for PVZ game state reading and action execution.
Can be used as a base for RL training or other AI approaches.

Usage:
    python main.py
    python main.py --debug
"""

import sys
import os
import time
import argparse
from datetime import datetime
from typing import Optional

# Import memory interface modules
from config import BotConfig
from utils.logger import Logger, LogLevel, get_logger, status_line, log_status

# Import data modules
from data.plants import PlantType, PLANT_COST, get_unlocked_plants
from data.zombies import ZombieType
from data.offsets import Offset

# Import memory modules
from memory.process import ProcessAttacher
from memory.reader import MemoryReader
from memory.writer import MemoryWriter
from memory.injector import AsmInjector

# Import game state modules
from game.state import GameState, SeedInfo
from game.zombie import ZombieInfo
from game.plant import PlantInfo
from game.grid import Grid

# Import engine modules
from engine.action import Action, ActionType


class PVZMemoryInterface:
    """
    Unified memory interface for PVZ (same as main.py)
    """
    
    def __init__(self):
        self.attacher = ProcessAttacher()
        self.reader: Optional[MemoryReader] = None
        self.writer: Optional[MemoryWriter] = None
        self.injector: Optional[AsmInjector] = None
        self.logger = get_logger()
    
    def attach(self) -> bool:
        """Attach to PVZ process"""
        if not self.attacher.attach():
            return False
        
        kernel32 = self.attacher.kernel32
        handle = self.attacher.handle
        
        self.reader = MemoryReader(kernel32, handle)
        self.writer = MemoryWriter(kernel32, handle)
        self.injector = AsmInjector(kernel32, handle, self.reader)
        
        return True
    
    def is_attached(self) -> bool:
        """Check if attached to process"""
        return self.attacher.is_attached()
    
    def is_in_game(self) -> bool:
        """Check if in game"""
        if not self.reader:
            return False
        return self.reader.is_in_game()
    
    def set_game_speed(self, speed: float) -> bool:
        """
        设置游戏速度倍率
        
        Args:
            speed: 速度倍率 (0.05 - 10.0)
                   1.0 = 正常速度
                   5.0 = 5倍速
                   10.0 = 10倍速 (最大)
        
        Returns:
            True if successful
        """
        if not self.writer or not self.reader:
            return False
        
        if speed < 0.05 or speed > 10.0:
            print(f"速度倍率超出范围 [0.05, 10.0]: {speed}")
            return False
        
        # TickMs = 10 / speed (默认10ms = 100fps)
        tick_ms = int(10 / speed + 0.5)
        tick_ms = max(1, min(200, tick_ms))  # 限制范围 1-200
        
        base = self.reader.get_base()
        if base == 0:
            return False
        
        self.writer.write_int(base + Offset.TICK_MS, tick_ms)
        return True
    
    def get_game_speed(self) -> float:
        """获取当前游戏速度倍率"""
        if not self.reader:
            return 1.0
        
        base = self.reader.get_base()
        if base == 0:
            return 1.0
        
        tick_ms = self.reader.read_int(base + Offset.TICK_MS)
        if tick_ms <= 0:
            return 1.0
        
        return 10.0 / tick_ms
    
    def get_game_state(self) -> Optional[GameState]:
        """Read complete game state"""
        if not self.reader or not self.reader.is_in_game():
            return None
        
        board = self.reader.get_board()
        if board == 0:
            return None
        
        # Read basic info
        sun = self.reader.get_sun()
        wave = self.reader.get_wave()
        total_waves = self.reader.get_total_waves()
        game_clock = self.reader.get_game_clock()
        scene = self.reader.get_scene()
        refresh_cd = self.reader.read_int(board + Offset.REFRESH_COUNTDOWN)
        huge_wave_cd = self.reader.read_int(board + Offset.HUGE_WAVE_COUNTDOWN)
        
        # Read zombies
        zombies = self._read_zombies(board)
        
        # Read plants and build grid
        plants, plant_grid = self._read_plants(board)
        
        # Read seeds
        seeds = self._read_seeds(board)
        
        # Read click_pao_countdown for cob cannon fire validation
        click_pao_cd = self.reader.read_int(board + Offset.CLICK_PAO_COUNTDOWN)
        
        # Read player inventory (仓库/已解锁植物)
        player_level = self.reader.get_player_level()
        player_coins = self.reader.get_player_coins()
        purchases = self.reader.get_all_purchases()
        unlocked_plants = get_unlocked_plants(player_level, purchases)
        
        # Read spawn lists (出怪列表)
        spawn_lists = self._read_spawn_lists(board, total_waves)
        
        return GameState(
            sun=sun,
            wave=wave,
            total_waves=total_waves,
            game_clock=game_clock,
            scene=scene,
            refresh_countdown=refresh_cd,
            huge_wave_countdown=huge_wave_cd,
            click_pao_countdown=click_pao_cd,
            zombies=zombies,
            plants=plants,
            seeds=seeds,
            plant_grid=plant_grid,
            player_level=player_level,
            player_coins=player_coins,
            unlocked_plants=unlocked_plants,
            spawn_lists=spawn_lists,
        )
    
    def _read_zombies(self, board: int) -> list:
        """Read all zombies from memory"""
        zombies = []
        zombie_array = self.reader.read_int(board + Offset.ZOMBIE_ARRAY)
        zombie_max = self.reader.read_int(board + Offset.ZOMBIE_COUNT_MAX)
        
        for i in range(min(zombie_max, 200)):
            addr = zombie_array + i * Offset.ZOMBIE_SIZE
            
            if self.reader.read_byte(addr + Offset.Z_DEAD):
                continue
            
            zombies.append(ZombieInfo(
                index=i,
                row=self.reader.read_int(addr + Offset.Z_ROW),
                x=self.reader.read_float(addr + Offset.Z_X),
                y=self.reader.read_float(addr + Offset.Z_Y),
                type=self.reader.read_int(addr + Offset.Z_TYPE),
                hp=self.reader.read_int(addr + Offset.Z_HP),
                hp_max=self.reader.read_int(addr + Offset.Z_HP_MAX),
                accessory_hp=self.reader.read_int(addr + Offset.Z_ACCESSORY_HP_1),
                state=self.reader.read_int(addr + Offset.Z_STATE),
                speed=self.reader.read_float(addr + Offset.Z_SPEED),
                slow_countdown=self.reader.read_int(addr + Offset.Z_SLOW_COUNTDOWN),
                freeze_countdown=self.reader.read_int(addr + Offset.Z_FREEZE_COUNTDOWN),
                butter_countdown=self.reader.read_int(addr + Offset.Z_BUTTER_COUNTDOWN),
                at_wave=self.reader.read_int(addr + Offset.Z_AT_WAVE),
            ))
        
        return zombies
    
    def _read_plants(self, board: int) -> tuple:
        """Read all plants and build grid"""
        plants = []
        grid = Grid()
        
        plant_array = self.reader.read_int(board + Offset.PLANT_ARRAY)
        plant_max = self.reader.read_int(board + Offset.PLANT_COUNT_MAX)
        
        for i in range(min(plant_max, 200)):
            addr = plant_array + i * Offset.PLANT_SIZE
            
            if self.reader.read_byte(addr + Offset.P_DEAD):
                continue
            
            row = self.reader.read_int(addr + Offset.P_ROW)
            col = self.reader.read_int(addr + Offset.P_COL)
            plant_type = self.reader.read_int(addr + Offset.P_TYPE)
            
            plant = PlantInfo(
                index=i,
                row=row,
                col=col,
                type=plant_type,
                hp=self.reader.read_int(addr + Offset.P_HP),
                hp_max=self.reader.read_int(addr + Offset.P_HP_MAX),
                state=self.reader.read_int(addr + Offset.P_STATE),
                shoot_countdown=self.reader.read_int(addr + Offset.P_SHOOT_COUNTDOWN),
                effective=self.reader.read_int(addr + Offset.P_EFFECTIVE) != 0,
                pumpkin_hp=self.reader.read_int(addr + Offset.P_PUMPKIN_HP),
                cob_countdown=self.reader.read_int(addr + Offset.P_COB_COUNTDOWN) if plant_type == PlantType.COBCANNON else 0,
                cob_ready=self.reader.read_bool(addr + Offset.P_COB_READY) if plant_type == PlantType.COBCANNON else False,
            )
            
            plants.append(plant)
            grid.set(row, col, plant)
        
        return plants, grid
    
    def _read_seeds(self, board: int) -> list:
        """Read seed cards"""
        seeds = []
        seed_array = self.reader.read_int(board + Offset.SEED_ARRAY)
        
        for i in range(10):
            addr = seed_array + i * Offset.SEED_SIZE
            seeds.append(SeedInfo(
                index=i,
                type=self.reader.read_int(addr + Offset.S_TYPE),
                recharge_countdown=self.reader.read_int(addr + Offset.S_RECHARGE_COUNTDOWN),
                recharge_time=self.reader.read_int(addr + Offset.S_RECHARGE_TIME),
                usable=self.reader.read_byte(addr + Offset.S_USABLE) != 0,
                imitator_type=self.reader.read_int(addr + Offset.S_IMITATOR_TYPE),
            ))
        
        return seeds
    
    def _read_spawn_lists(self, board: int, total_waves: int) -> list:
        """Read zombie spawn lists for all waves"""
        all_waves = []
        max_waves = min(total_waves, Offset.ZOMBIE_LIST_MAX_WAVES)
        
        for wave in range(max_waves):
            wave_zombies = []
            base = board + Offset.ZOMBIE_LIST + wave * Offset.ZOMBIE_LIST_WAVE_SIZE
            
            for i in range(Offset.ZOMBIE_LIST_MAX_PER_WAVE):
                zombie_type = self.reader.read_int(base + i * 4)
                if zombie_type != -1:  # -1 表示空槽位
                    wave_zombies.append(zombie_type)
            
            all_waves.append(wave_zombies)
        
        return all_waves
    
    def plant(self, row: int, col: int, plant_type: int) -> bool:
        """Plant at position"""
        if not self.injector:
            return False
        return self.injector.plant(row, col, plant_type)
    
    def shovel(self, row: int, col: int) -> bool:
        """Remove plant at position"""
        if not self.injector:
            return False
        return self.injector.shovel(row, col)
    
    def collect_all_items(self) -> int:
        """Collect all items (sun, coins)"""
        if not self.reader or not self.writer:
            return 0
        
        board = self.reader.get_board()
        if board == 0:
            return 0
        
        count = 0
        item_array = self.reader.read_int(board + Offset.ITEM_ARRAY)
        item_max = self.reader.read_int(board + Offset.ITEM_COUNT_MAX)
        
        for i in range(min(item_max, 100)):
            addr = item_array + i * Offset.ITEM_SIZE
            
            if self.reader.read_byte(addr + Offset.I_DISAPPEARED):
                continue
            if self.reader.read_byte(addr + Offset.I_COLLECTED):
                continue
            
            self.writer.write_byte(addr + Offset.I_COLLECTED, 1)
            count += 1
        
        return count
    
    def restart_level(self) -> bool:
        """
        Restart current level via direct memory operation.
        
        Calls MakeNewBoard() which resets the level while keeping same scene.
        This is much faster and more reliable than keyboard simulation.
        """
        if not self.injector:
            return False
        
        return self.injector.make_new_board()
    
    def set_adventure_level(self, level: int) -> bool:
        """
        Set adventure mode level (1-50).
        
        Level mapping:
            1-10 = Day levels (1-1 to 1-10)
            11-20 = Night levels (2-1 to 2-10)
            21-30 = Pool levels (3-1 to 3-10)
            31-40 = Fog levels (4-1 to 4-10)
            41-50 = Roof levels (5-1 to 5-10)
        
        After setting, you need to enter adventure mode to play that level.
        
        Args:
            level: Level number 1-50
            
        Returns:
            True if successful
        """
        if not self.reader or not self.writer:
            return False
        
        base = self.reader.read_int(Offset.BASE)
        if not base:
            return False
        
        player_info = self.reader.read_int(base + Offset.PLAYER_INFO)
        if not player_info:
            return False
        
        # Level is stored at PlayerInfo + 0x24
        return self.writer.write_int(player_info + Offset.PI_LEVEL, level)

    @property
    def pid(self) -> Optional[int]:
        """Get process ID"""
        return self.attacher.pid


def main():
    """Main entry point - Demo of memory interface"""
    parser = argparse.ArgumentParser(description="PVZ Memory Interface")
    parser.add_argument("--debug", action="store_true", help="Enable debug mode")
    parser.add_argument("--no-collect", action="store_true", help="Disable auto-collecting")
    parser.add_argument("--no-log", action="store_true", help="Disable log file")
    parser.add_argument("--log-file", type=str, default=None, help="Log file path")
    args = parser.parse_args()
    
    # Setup logging
    log_file = None
    if not args.no_log:
        if args.log_file:
            log_file = args.log_file
        else:
            log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs")
            os.makedirs(log_dir, exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            log_file = os.path.join(log_dir, f"pvz_{timestamp}.log")
        print(f"📝 日志将保存到: {log_file}")
    
    # Create config
    config = BotConfig()
    if args.debug:
        config.debug = True
        config.log_level = 0
    if args.no_collect:
        config.auto_collect_sun = False
    
    # Initialize global logger
    import utils.logger as logger_module
    log_level = LogLevel.DEBUG if args.debug else LogLevel.INFO
    logger_module._global_logger = Logger("PVZ", level=log_level, file_path=log_file)
    
    logger = get_logger()
    
    # Create memory interface
    memory = PVZMemoryInterface()
    
    print("=" * 60)
    print("  PVZ Memory Interface")
    print("  Ready for RL training or other AI approaches")
    print("=" * 60)
    
    # Wait for PVZ process
    logger.info("Waiting for PVZ process...")
    while not memory.attach():
        print(".", end="", flush=True)
        time.sleep(1)
    print()
    
    logger.info(f"Attached to PVZ (PID: {memory.pid})")
    
    # Wait for entering a game level
    logger.info("Waiting for game to start (enter a level)...")
    while not memory.is_in_game():
        print(".", end="", flush=True)
        time.sleep(0.5)
        if not memory.is_attached():
            logger.warning("Lost connection, re-attaching...")
            while not memory.attach():
                time.sleep(1)
    print()
    
    logger.info("游戏已检测到，开始监控...")
    print("-" * 60)
    print("  📊 监控模式 | 按 Ctrl+C 停止")
    print("-" * 60)
    
    # Main loop - just monitor and display state
    try:
        while True:
            if not memory.is_attached():
                logger.warning("Lost connection to PVZ, trying to reconnect...")
                while not memory.attach():
                    time.sleep(1)
                logger.info(f"Reconnected to PVZ (PID: {memory.pid})")
            
            if not memory.is_in_game():
                status_line("[Waiting] Level ended or not in game, waiting...")
                time.sleep(0.5)
                continue
            
            # Auto-collect items
            if config.auto_collect_sun:
                memory.collect_all_items()
            
            # Read and display state
            state = memory.get_game_state()
            if state:
                log_status(
                    wave=state.wave,
                    total_waves=state.total_waves,
                    sun=state.sun,
                    plants=state.plant_count,
                    zombies=state.zombie_count,
                    llm_calls=0,
                    actions=0,
                    llm_busy=False,
                    pending=0
                )
            else:
                status_line("[等待] 正在读取游戏状态...")
            
            time.sleep(0.1)
            
    except KeyboardInterrupt:
        print("\n")
        logger.info("Stopped by user")
    finally:
        if logger_module._global_logger:
            logger_module._global_logger.close()


if __name__ == "__main__":
    main()
