"""
Emergency Handler

Local rule-based emergency response that doesn't wait for LLM.
Handles critical situations requiring immediate action.
"""

from typing import List, Optional
from dataclasses import dataclass

from game.state import GameState
from game.zombie import ZombieInfo
from engine.action import Action, ActionType
from data.plants import PlantType, PLANT_COST, INSTANT_KILL_PLANTS, DEFENSIVE_PLANTS
from data.zombies import ZombieType, GARGANTUAR_ZOMBIES
from data.offsets import SceneType

# Priority order for emergency plants (higher = more preferred)
# Format: (PlantType, priority, effect_type)
# effect_type: 'instant' = kills instantly, 'defense' = blocks, 'delay' = stalls
# NOTE: Sunflower removed from delay list - never sacrifice economy!
EMERGENCY_PLANT_PRIORITY = [
    # Instant kills (highest priority)
    (PlantType.CHERRY_BOMB, 100, 'instant'),   # 150 sun, AOE
    (PlantType.JALAPENO, 95, 'instant'),       # 125 sun, row clear
    (PlantType.SQUASH, 90, 'instant'),         # 50 sun, single target
    (PlantType.DOOMSHROOM, 88, 'instant'),     # 125 sun, huge AOE (needs awake)
    (PlantType.CHOMPER, 85, 'instant'),        # 150 sun, single target
    (PlantType.POTATO_MINE, 80, 'instant'),    # 25 sun, needs arming time
    (PlantType.HYPNOSHROOM, 75, 'instant'),    # 75 sun, turns zombie
    (PlantType.TANGLEKELP, 70, 'instant'),     # 25 sun, water only
    
    # Defensive plants (block zombies)
    (PlantType.TALLNUT, 65, 'defense'),        # 125 sun
    (PlantType.WALLNUT, 60, 'defense'),        # 50 sun
    (PlantType.PUMPKIN, 55, 'defense'),        # 125 sun, overlay
    (PlantType.GARLIC, 50, 'defense'),         # 50 sun, redirects
    
    # Delay plants (chump block) - cheap expendables only!
    (PlantType.PUFFSHROOM, 45, 'delay'),       # 0 sun!
    (PlantType.SUNSHROOM, 40, 'delay'),        # 25 sun
    (PlantType.FLOWERPOT, 35, 'delay'),        # 25 sun
    # Sunflower intentionally NOT included - never sacrifice economy!
    (PlantType.LILYPAD, 25, 'delay'),          # 25 sun (water)
]


@dataclass
class EmergencyAction:
    """Emergency action with metadata"""
    action: Action
    urgency: int  # 0-100, higher = more urgent
    reason: str


class EmergencyHandler:
    """
    Local rule engine for emergency situations.
    
    Handles:
    - Zombies very close to home (x < 150)
    - Fast zombies approaching
    - No defense in threatened row
    """
    
    def __init__(self, emergency_x: int = 150, emergency_eta: int = 200):
        """
        Initialize handler.
        
        Args:
            emergency_x: X position threshold for emergency
            emergency_eta: ETA threshold in cs for emergency
        """
        self.emergency_x = emergency_x
        self.emergency_eta = emergency_eta
    
    def check(self, state: GameState) -> Optional[EmergencyAction]:
        """
        Check for emergency situations and return immediate action.
        
        Args:
            state: Current game state
            
        Returns:
            Emergency action if needed, None otherwise
        """
        emergencies = []
        row_count = SceneType.get_row_count(state.scene)
        
        # Check each row for emergencies
        for row in range(row_count):
            row_emergency = self._check_row_emergency(state, row)
            if row_emergency:
                emergencies.append(row_emergency)
        
        if not emergencies:
            return None
        
        # Return highest urgency emergency
        emergencies.sort(key=lambda e: e.urgency, reverse=True)
        return emergencies[0]
    
    def _check_row_emergency(self, state: GameState, row: int) -> Optional[EmergencyAction]:
        """Check for emergency in a specific row"""
        row_zombies = state.get_zombies_in_row(row)
        if not row_zombies:
            return None
        
        # Find most dangerous zombie
        closest = min(row_zombies, key=lambda z: z.x)
        
        # Check if emergency
        is_emergency = (
            closest.x < self.emergency_x or
            (closest.effective_speed > 0 and 
             closest.time_to_reach(0) < self.emergency_eta)
        )
        
        if not is_emergency:
            return None
        
        # Determine best response
        return self._get_emergency_response(state, row, closest, row_zombies)
    
    def _get_available_emergency_plants(self, state: GameState) -> List[tuple]:
        """
        Get list of emergency plants that the player actually has in their card slots.
        Returns list of (PlantType, priority, effect_type) sorted by priority.
        """
        available = []
        player_plant_types = {seed.type for seed in state.seeds if seed.type >= 0}
        
        for plant_type, priority, effect_type in EMERGENCY_PLANT_PRIORITY:
            if plant_type in player_plant_types:
                available.append((plant_type, priority, effect_type))
        
        return available
    
    def _get_emergency_response(self, state: GameState, row: int,
                                 closest: ZombieInfo,
                                 row_zombies: List[ZombieInfo]) -> Optional[EmergencyAction]:
        """Determine best emergency response based on available cards"""
        urgency = self._calculate_urgency(closest)
        
        # Get available emergency plants from player's actual card slots
        available_plants = self._get_available_emergency_plants(state)
        
        # 1. Try cob cannon first (if available, it's the best)
        cob_action = self._try_cob(state, row, closest, row_zombies)
        if cob_action:
            return EmergencyAction(
                action=cob_action,
                urgency=urgency,
                reason=f"紧急: 玉米炮轰击r{row} ({len(row_zombies)}只僵尸)"
            )
        
        # 2. Try plants based on what player actually has, in priority order
        for plant_type, priority, effect_type in available_plants:
            action = self._try_emergency_plant(state, row, closest, plant_type, effect_type)
            if action:
                from llm.encoder import PLANT_NAMES
                plant_name = PLANT_NAMES.get(plant_type, f"植物{plant_type}")
                return EmergencyAction(
                    action=action,
                    urgency=urgency - (100 - priority) // 10,
                    reason=f"紧急: {plant_name} r{row}"
                )
        
        return None

    def _try_emergency_plant(self, state: GameState, row: int, 
                             closest: ZombieInfo, plant_type: int, 
                             effect_type: str) -> Optional[Action]:
        """
        Try to use a specific emergency plant.
        Returns Action if possible, None otherwise.
        """
        if not state.can_plant(plant_type):
            return None
            
        target_col = closest.col
        
        if effect_type == 'instant':
            # Instant kill plants: place near zombie
            for col_offset in [0, -1, 1, -2, 2]:
                col = target_col + col_offset
                if 0 <= col <= 8 and state.is_cell_empty(row, col):
                    return Action.plant(
                        row=row,
                        col=col,
                        plant_type=plant_type,
                        priority=90,
                        reason="紧急秒杀"
                    )
        
        elif effect_type == 'defense':
            # Defensive plants: place between zombie and house
            start_col = min(8, target_col)
            for col in range(start_col, -1, -1):
                if state.is_cell_empty(row, col):
                    return Action.plant(
                        row=row,
                        col=col,
                        plant_type=plant_type,
                        priority=70,
                        reason="紧急防御"
                    )
        
        elif effect_type == 'delay':
            # Delay plants (chump block): place right in front of zombie
            if 0 <= target_col <= 8 and state.is_cell_empty(row, target_col):
                return Action.plant(
                    row=row,
                    col=target_col,
                    plant_type=plant_type,
                    priority=100,
                    reason="紧急肉盾"
                )
        
        return None
    
    def _calculate_urgency(self, zombie: ZombieInfo) -> int:
        """Calculate urgency based on zombie position and type"""
        # Base urgency from position
        if zombie.x < 50:
            urgency = 100
        elif zombie.x < 100:
            urgency = 90
        elif zombie.x < 150:
            urgency = 80
        else:
            urgency = 70
        
        # Bonus for dangerous zombies
        if zombie.type in GARGANTUAR_ZOMBIES:
            urgency = min(100, urgency + 10)
        elif zombie.type == ZombieType.FOOTBALL:
            urgency = min(100, urgency + 5)
        
        return urgency
    
    def _try_cob(self, state: GameState, row: int, closest: ZombieInfo,
                 row_zombies: List[ZombieInfo]) -> Optional[Action]:
        """Try to use cob cannon"""
        ready_cobs = state.get_ready_cobs()
        if not ready_cobs or not state.can_fire_cob():
            return None
        
        # Calculate optimal target position
        target_x = closest.x
        
        # Adjust for flying time (~373cs)
        if closest.effective_speed > 0:
            target_x -= closest.effective_speed * 373
        
        # Clamp to valid range
        target_x = max(0, min(800, target_x))
        
        return Action.use_cob(
            target_x=target_x,
            target_row=row,
            priority=100,
            reason=f"紧急炮击"
        )
    
    def _try_jalapeno(self, state: GameState, row: int) -> Optional[Action]:
        """Try to use jalapeno"""
        if not state.can_plant(PlantType.JALAPENO):
            return None
        
        # Find empty cell in row (prefer middle columns)
        for col in [4, 3, 5, 2, 6, 1, 7, 0, 8]:
            if state.is_cell_empty(row, col):
                return Action.use_jalapeno(
                    row=row,
                    col=col,
                    priority=95,
                    reason="紧急辣椒"
                )
        
        return None
    
    def _try_cherry(self, state: GameState, row: int,
                    closest: ZombieInfo) -> Optional[Action]:
        """Try to use cherry bomb"""
        if not state.can_plant(PlantType.CHERRY_BOMB):
            return None
        
        # Find empty cell near zombie
        target_col = closest.col
        
        for col_offset in [0, -1, 1, -2, 2]:
            col = target_col + col_offset
            if 0 <= col <= 8 and state.is_cell_empty(row, col):
                return Action.use_cherry(
                    row=row,
                    col=col,
                    priority=90,
                    reason="紧急樱桃"
                )
        
        return None
    
    def _try_emergency_wall(self, state: GameState, row: int,
                            closest: ZombieInfo) -> Optional[Action]:
        """Try to plant emergency wall"""
        # Check if we have wall available
        can_wallnut = state.can_plant(PlantType.WALLNUT)
        can_tallnut = state.can_plant(PlantType.TALLNUT)
        
        if not can_wallnut and not can_tallnut:
            return None
        
        # Find good position for wall (between zombie and home)
        zombie_col = closest.col
        
        # Try to plant as close to zombie as possible to block immediately
        # But not ON the zombie
        start_col = min(8, zombie_col)
        
        for col in range(start_col, -1, -1):
            if state.is_cell_empty(row, col):
                plant_type = PlantType.TALLNUT if can_tallnut else PlantType.WALLNUT
                return Action.plant(
                    row=row,
                    col=col,
                    plant_type=plant_type,
                    priority=70,
                    reason="紧急补墙"
                )
        
        return None

    def _try_squash(self, state: GameState, row: int, closest: ZombieInfo) -> Optional[Action]:
        """Try to use squash"""
        if not state.can_plant(PlantType.SQUASH):
            return None
            
        # Squash can be planted on the zombie or right next to it
        target_col = closest.col
        
        # Try current col and adjacent cols
        for col in [target_col, target_col + 1, target_col - 1]:
            if 0 <= col <= 8 and state.is_cell_empty(row, col):
                return Action.plant(
                    row=row,
                    col=col,
                    plant_type=PlantType.SQUASH,
                    priority=92,
                    reason="紧急窝瓜"
                )
        return None

    def _try_potato_mine(self, state: GameState, row: int, closest: ZombieInfo) -> Optional[Action]:
        """Try to use potato mine"""
        if not state.can_plant(PlantType.POTATOMINE):
            return None
            
        # Potato mine needs time to arm, so plant it further back if possible
        # But in emergency, just plant it anywhere
        target_col = closest.col
        
        for col in range(target_col, -1, -1):
            if state.is_cell_empty(row, col):
                return Action.plant(
                    row=row,
                    col=col,
                    plant_type=PlantType.POTATOMINE,
                    priority=85,
                    reason="紧急土豆雷"
                )
        return None

    def _try_chump_block(self, state: GameState, row: int, closest: ZombieInfo) -> Optional[Action]:
        """Try to plant ANYTHING cheap to block the zombie"""
        # List of cheap plants to sacrifice
        cheap_plants = [
            PlantType.PUFFSHROOM, # Free!
            PlantType.SUNFLOWER,  # 50
            PlantType.FLOWERPOT,  # 25
            PlantType.GARLIC,     # 50
        ]
        
        available_plant = -1
        for pt in cheap_plants:
            if state.can_plant(pt):
                available_plant = pt
                break
        
        if available_plant == -1:
            return None
            
        # Plant right in front of zombie
        target_col = closest.col
        if 0 <= target_col <= 8 and state.is_cell_empty(row, target_col):
             return Action.plant(
                row=row,
                col=target_col,
                plant_type=available_plant,
                priority=100, # Desperate!
                reason="紧急肉盾"
            )
            
        return None

    def get_all_emergencies(self, state: GameState) -> List[EmergencyAction]:
        """Get all emergency situations (for reporting)"""
        emergencies = []
        row_count = SceneType.get_row_count(state.scene)
        
        for row in range(row_count):
            row_emergency = self._check_row_emergency(state, row)
            if row_emergency:
                emergencies.append(row_emergency)
        
        return emergencies
