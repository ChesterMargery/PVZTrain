"""
Reflex Layer - Enhanced Local Decision Making

Extends EmergencyHandler with more aggressive local rules.
Handles deterministic actions that don't need LLM thinking:

1. Immediate threats (x < 300) - expanded from emergency (x < 150)
2. Safe row sunflower planting
3. Auto-replacement of eaten plants
4. Cob cannon auto-targeting on clusters
5. Instant-use cards when optimal

This reduces LLM dependency and provides sub-20ms response time.
"""

from typing import Optional, List, Tuple
from dataclasses import dataclass

from game.state import GameState
from game.zombie import ZombieInfo
from engine.action import Action, ActionType
from data.plants import PlantType, PLANT_COST, ATTACKING_PLANTS, SUN_PRODUCING_PLANTS
from data.zombies import ZombieType, GARGANTUAR_ZOMBIES
from data.offsets import SceneType


@dataclass
class ReflexAction:
    """A reflexive action with metadata"""
    action: Action
    confidence: float  # 0.0 - 1.0, how confident we are this is correct
    reason: str
    category: str  # 'emergency', 'economic', 'tactical', 'defensive'


class ReflexLayer:
    """
    Enhanced local decision layer.
    
    Makes fast, rule-based decisions for situations that don't
    require LLM strategic thinking.
    """
    
    def __init__(self, 
                 threat_x_threshold: int = 300,
                 safe_col_threshold: int = 5,
                 cluster_threshold: int = 4):
        """
        Initialize reflex layer.
        
        Args:
            threat_x_threshold: X position below which zombies are "threatening"
            safe_col_threshold: Columns 0 to this are "safe" for sunflowers
            cluster_threshold: Number of zombies to trigger AOE
        """
        self.threat_x = threat_x_threshold
        self.safe_col = safe_col_threshold
        self.cluster_threshold = cluster_threshold
        
        # Track what we've already done this tick
        self._actions_this_tick: List[str] = []
    
    def get_reflex_actions(self, state: GameState) -> List[ReflexAction]:
        """
        Get all applicable reflex actions for current state.
        
        Returns actions sorted by priority (highest first).
        """
        self._actions_this_tick.clear()
        actions = []
        
        # 1. Check for immediate threats (highest priority)
        threat_actions = self._check_immediate_threats(state)
        actions.extend(threat_actions)
        
        # 2. Check for optimal cob cannon shots
        cob_actions = self._check_cob_opportunities(state)
        actions.extend(cob_actions)
        
        # 3. Check for safe sunflower placement (if early game)
        if state.wave <= 5 and state.sun >= 50:
            sun_actions = self._check_sunflower_placement(state)
            actions.extend(sun_actions)
        
        # 4. Check for auto-replacement opportunities
        replace_actions = self._check_replacements(state)
        actions.extend(replace_actions)
        
        # 5. Check for cherry bomb clusters
        cherry_actions = self._check_cherry_clusters(state)
        actions.extend(cherry_actions)
        
        # Sort by confidence (highest first)
        actions.sort(key=lambda a: a.confidence, reverse=True)
        
        return actions
    
    def get_best_action(self, state: GameState) -> Optional[ReflexAction]:
        """Get the single best reflex action, if any."""
        actions = self.get_reflex_actions(state)
        return actions[0] if actions else None
    
    def _check_immediate_threats(self, state: GameState) -> List[ReflexAction]:
        """Check for zombies that need immediate response"""
        actions = []
        row_count = SceneType.get_row_count(state.scene)
        
        for row in range(row_count):
            zombies = state.get_zombies_in_row(row)
            if not zombies:
                continue
            
            # Find closest zombie
            closest = min(zombies, key=lambda z: z.x)
            
            if closest.x < self.threat_x:
                # Need to respond to this threat
                action = self._get_threat_response(state, row, closest, zombies)
                if action:
                    actions.append(action)
        
        return actions
    
    def _get_threat_response(self, state: GameState, row: int,
                             closest: ZombieInfo, 
                             row_zombies: List[ZombieInfo]) -> Optional[ReflexAction]:
        """Determine best response to a threatening zombie"""
        
        # Priority 1: If it's a Gargantuar, we need serious firepower
        if closest.type in GARGANTUAR_ZOMBIES:
            # Try cob cannon
            if state.can_fire_cob():
                cob_action = self._create_cob_action(state, row, closest.x)
                if cob_action:
                    return ReflexAction(
                        action=cob_action,
                        confidence=0.95,
                        reason=f"巨人威胁 r{row}",
                        category='emergency'
                    )
            
            # Try cherry bomb
            if state.can_plant(PlantType.CHERRY_BOMB):
                col = closest.col
                if 0 <= col <= 8 and state.is_cell_empty(row, col):
                    return ReflexAction(
                        action=Action.plant(row, col, PlantType.CHERRY_BOMB, 100),
                        confidence=0.9,
                        reason=f"樱桃炸巨人 r{row}",
                        category='emergency'
                    )
        
        # Priority 2: Check row density for AOE
        if len(row_zombies) >= self.cluster_threshold:
            # Try jalapeno (clears whole row)
            if state.can_plant(PlantType.JALAPENO):
                for col in [4, 3, 5, 2, 6, 1, 7]:
                    if state.is_cell_empty(row, col):
                        return ReflexAction(
                            action=Action.plant(row, col, PlantType.JALAPENO, 95),
                            confidence=0.85,
                            reason=f"辣椒清行 r{row} ({len(row_zombies)}只)",
                            category='emergency'
                        )
        
        # Priority 3: Single zombie, use squash/chomper
        if closest.x < 200:
            if state.can_plant(PlantType.SQUASH):
                col = closest.col
                if 0 <= col <= 8 and state.is_cell_empty(row, col):
                    return ReflexAction(
                        action=Action.plant(row, col, PlantType.SQUASH, 90),
                        confidence=0.8,
                        reason=f"窝瓜压制 r{row}",
                        category='emergency'
                    )
        
        # Priority 4: Block with wall
        if closest.x < 150:
            wall_type = None
            if state.can_plant(PlantType.TALLNUT):
                wall_type = PlantType.TALLNUT
            elif state.can_plant(PlantType.WALLNUT):
                wall_type = PlantType.WALLNUT
            
            if wall_type:
                # Find empty cell between zombie and house
                for col in range(min(8, closest.col), -1, -1):
                    if state.is_cell_empty(row, col):
                        return ReflexAction(
                            action=Action.plant(row, col, wall_type, 70),
                            confidence=0.75,
                            reason=f"紧急补墙 r{row}",
                            category='emergency'
                        )
        
        return None
    
    def _check_cob_opportunities(self, state: GameState) -> List[ReflexAction]:
        """Check for optimal cob cannon targets"""
        actions = []
        
        if not state.can_fire_cob():
            return actions
        
        row_count = SceneType.get_row_count(state.scene)
        
        # Look for clusters of zombies
        best_target = None
        best_count = 0
        
        for row in range(row_count):
            zombies = state.get_zombies_in_row(row)
            
            # Group zombies by X position (cob has ~115px radius)
            for z in zombies:
                # Count zombies within cob radius
                count = sum(1 for other in state.zombies 
                           if other.hp > 0 and
                           abs(other.x - z.x) < 115 and
                           abs(other.row - row) <= 1)
                
                if count >= 6 and count > best_count:
                    best_count = count
                    best_target = (row, z.x)
        
        if best_target and best_count >= 6:
            row, x = best_target
            # Account for cob flight time (~373cs)
            target_x = x - 50  # Slight lead
            
            action = Action.use_cob(
                target_x=target_x,
                target_row=row,
                priority=85,
                reason=f"炮击{best_count}只"
            )
            
            actions.append(ReflexAction(
                action=action,
                confidence=0.9,
                reason=f"集群炮击 r{row} ({best_count}只)",
                category='tactical'
            ))
        
        return actions
    
    def _check_sunflower_placement(self, state: GameState) -> List[ReflexAction]:
        """Check for safe sunflower placement opportunities"""
        actions = []
        
        if not state.can_plant(PlantType.SUNFLOWER):
            return actions
        
        row_count = SceneType.get_row_count(state.scene)
        
        # Count current sunflowers
        sunflower_count = sum(1 for p in state.alive_plants 
                              if p.type == PlantType.SUNFLOWER)
        
        # Early game: prioritize sunflowers
        if sunflower_count < 6 and state.wave <= 3:
            for row in range(row_count):
                # Check if row is safe (no zombies close)
                row_zombies = state.get_zombies_in_row(row)
                if row_zombies:
                    closest = min(row_zombies, key=lambda z: z.x)
                    if closest.x < 600:
                        continue
                
                # Find safe column for sunflower
                for col in range(min(2, self.safe_col), -1, -1):
                    if state.is_cell_empty(row, col):
                        actions.append(ReflexAction(
                            action=Action.plant(row, col, PlantType.SUNFLOWER, 40),
                            confidence=0.7,
                            reason=f"安全种花 r{row}c{col}",
                            category='economic'
                        ))
                        return actions  # Only one sunflower at a time
        
        return actions
    
    def _check_replacements(self, state: GameState) -> List[ReflexAction]:
        """Check for plants that need replacement"""
        actions = []
        
        # Check for damaged walls that need replacement
        for plant in state.alive_plants:
            if plant.type in [PlantType.WALLNUT, PlantType.TALLNUT]:
                # If wall HP < 30%, consider replacement
                if plant.hp_percent < 0.3:
                    # Check if we can plant a new wall
                    replacement_type = plant.type
                    if state.can_plant(replacement_type):
                        # Can we shovel and replace?
                        actions.append(ReflexAction(
                            action=Action.shovel(plant.row, plant.col),
                            confidence=0.6,
                            reason=f"铲除损坏的墙 r{plant.row}c{plant.col}",
                            category='defensive'
                        ))
        
        return actions
    
    def _check_cherry_clusters(self, state: GameState) -> List[ReflexAction]:
        """Check for zombie clusters worth cherry bombing"""
        actions = []
        
        if not state.can_plant(PlantType.CHERRY_BOMB):
            return actions
        
        row_count = SceneType.get_row_count(state.scene)
        
        # Find best cherry target (3x3 area)
        for row in range(row_count):
            zombies = state.get_zombies_in_row(row)
            
            for z in zombies:
                # Count zombies in 3x3 cherry range
                count = 0
                for other in state.zombies:
                    if other.hp <= 0:
                        continue
                    if abs(other.row - row) <= 1:
                        # Cherry range is roughly 3 columns wide
                        col_diff = abs(other.col - z.col)
                        if col_diff <= 1:
                            count += 1
                
                # If cluster is big enough, cherry is worth it
                if count >= 5:
                    col = z.col
                    if 0 <= col <= 8 and state.is_cell_empty(row, col):
                        actions.append(ReflexAction(
                            action=Action.plant(row, col, PlantType.CHERRY_BOMB, 88),
                            confidence=0.85,
                            reason=f"樱桃炸群 r{row} ({count}只)",
                            category='tactical'
                        ))
        
        return actions
    
    def _create_cob_action(self, state: GameState, row: int, 
                           target_x: float) -> Optional[Action]:
        """Create a cob cannon action"""
        if not state.can_fire_cob():
            return None
        
        return Action.use_cob(
            target_x=target_x,
            target_row=row,
            priority=95,
            reason="反射炮击"
        )


def integrate_reflex_layer(player) -> None:
    """
    Integrate ReflexLayer into an LLMPlayer instance.
    
    Call this after creating the player to add reflex capabilities.
    """
    from llm.config import get_config
    
    config = get_config()
    if not config.enhanced_reflex:
        return
    
    player.reflex_layer = ReflexLayer(
        threat_x_threshold=config.reflex_x_threshold
    )
    
    # Store original fast loop handler
    original_handle_emergencies = player._handle_emergencies
    
    async def enhanced_handle_emergencies():
        """Enhanced emergency handling with reflex layer"""
        # First, run original emergency handler
        await original_handle_emergencies()
        
        # Then check reflex layer for additional actions
        if player.state.game_state and hasattr(player, 'reflex_layer'):
            reflex_action = player.reflex_layer.get_best_action(player.state.game_state)
            
            if reflex_action and reflex_action.confidence >= 0.8:
                # High confidence reflex action - execute immediately
                await player._execute_action(reflex_action.action)
    
    player._handle_emergencies = enhanced_handle_emergencies
