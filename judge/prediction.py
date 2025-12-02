"""
Movement Prediction Module
Predicts zombie positions and timing for optimal attacks
"""

from typing import Optional, Tuple, List
from data.constants import (
    COB_FLY_TIME,
    CHERRY_DELAY,
    GIGA_AVG_SPEED,
    GLOOM_DAMAGE_PER_CS,
    GRID_WIDTH,
    LAWN_LEFT_X,
)
from data.zombies import (
    ZombieType,
    ZOMBIE_BASE_SPEED,
    SLOW_SPEED_MULTIPLIER,
    is_gargantuar,
)


def get_effective_speed(zombie_speed: float, 
                        is_slowed: bool = False, 
                        is_frozen: bool = False) -> float:
    """
    Calculate effective zombie speed considering status effects
    
    Args:
        zombie_speed: Base zombie speed
        is_slowed: Whether zombie is slowed
        is_frozen: Whether zombie is frozen
        
    Returns:
        Effective speed in pixels per cs
    """
    if is_frozen:
        return 0.0
    if is_slowed:
        return zombie_speed * SLOW_SPEED_MULTIPLIER
    return zombie_speed


def predict_position(zombie_x: float, zombie_speed: float, time_cs: float,
                     is_slowed: bool = False, is_frozen: bool = False) -> float:
    """
    Predict zombie x position after a given time
    
    Args:
        zombie_x: Current x position
        zombie_speed: Current speed
        time_cs: Time in centiseconds
        is_slowed: Whether zombie is slowed
        is_frozen: Whether zombie is frozen
        
    Returns:
        Predicted x position
    """
    effective_speed = get_effective_speed(zombie_speed, is_slowed, is_frozen)
    return zombie_x - effective_speed * time_cs


def time_to_reach(zombie_x: float, target_x: float, zombie_speed: float,
                  is_slowed: bool = False, is_frozen: bool = False) -> float:
    """
    Calculate time for zombie to reach a target x position
    
    Args:
        zombie_x: Current zombie x position
        target_x: Target x position
        zombie_speed: Zombie speed
        is_slowed: Whether zombie is slowed
        is_frozen: Whether zombie is frozen
        
    Returns:
        Time in centiseconds, or float('inf') if cannot reach
    """
    effective_speed = get_effective_speed(zombie_speed, is_slowed, is_frozen)
    
    if effective_speed <= 0:
        return float('inf')
    
    distance = zombie_x - target_x
    if distance <= 0:
        return 0.0  # Already past target
    
    return distance / effective_speed


def move_time(zombie_x: float, distance: float, zombie_speed: float,
              slow_countdown: int = 0, freeze_countdown: int = 0) -> float:
    """
    Calculate time to move a certain distance considering status effects
    
    This accounts for status effects wearing off during movement.
    
    Args:
        zombie_x: Current x position
        distance: Distance to travel
        zombie_speed: Base zombie speed
        slow_countdown: Remaining slow time (cs)
        freeze_countdown: Remaining freeze time (cs)
        
    Returns:
        Total time in centiseconds
    """
    if distance <= 0:
        return 0.0
    
    total_time = 0.0
    remaining_distance = distance
    
    # First, handle freeze time
    if freeze_countdown > 0:
        total_time += freeze_countdown
        # No movement during freeze
    
    # Then, handle slow time
    if slow_countdown > freeze_countdown:
        slow_remaining = slow_countdown - freeze_countdown
        slowed_speed = zombie_speed * SLOW_SPEED_MULTIPLIER
        if slowed_speed > 0:
            distance_while_slowed = slowed_speed * slow_remaining
            if distance_while_slowed >= remaining_distance:
                # Reaches destination while slowed
                return total_time + remaining_distance / slowed_speed
            else:
                total_time += slow_remaining
                remaining_distance -= distance_while_slowed
    
    # Normal speed for remaining distance
    if zombie_speed > 0 and remaining_distance > 0:
        total_time += remaining_distance / zombie_speed
    elif remaining_distance > 0:
        return float('inf')
    
    return total_time


# ============================================================================
# Gargantuar Specific Predictions
# ============================================================================

def is_giga_io_dead(zombie_hp: int, zombie_x: float, 
                    gloom_count: int, time_available_cs: float) -> bool:
    """
    Check if a Giga Gargantuar can be killed by Gloom-shrooms before reaching target
    
    "IO" refers to the I/O (Interception/Obliteration) strategy in PVZ.
    
    Args:
        zombie_hp: Current Giga HP
        zombie_x: Current x position
        gloom_count: Number of Gloom-shrooms affecting the zombie
        time_available_cs: Time until zombie reaches danger zone
        
    Returns:
        True if gloom damage will kill the Giga in time
    """
    if gloom_count <= 0:
        return False
    
    total_dps = GLOOM_DAMAGE_PER_CS * gloom_count
    damage_dealt = total_dps * time_available_cs
    
    return damage_dealt >= zombie_hp


def predict_giga_position(zombie_x: float, time_cs: float,
                          is_attacking: bool = False) -> float:
    """
    Predict Giga Gargantuar position accounting for attack animations
    
    Uses average speed that accounts for smash animation time.
    
    Args:
        zombie_x: Current x position
        time_cs: Time in centiseconds
        is_attacking: Whether Giga is currently attacking
        
    Returns:
        Predicted x position
    """
    # Use average speed that accounts for attack animations
    return zombie_x - GIGA_AVG_SPEED * time_cs


def get_optimal_cob_timing(zombie_x: float, zombie_speed: float,
                           target_col: float) -> float:
    """
    Calculate optimal time to fire cob cannon to hit a moving zombie
    
    Args:
        zombie_x: Current zombie x position
        zombie_speed: Zombie speed
        target_col: Target column for cob
        
    Returns:
        Time to wait before firing (cs)
    """
    target_x = LAWN_LEFT_X + target_col * GRID_WIDTH
    
    # Solve for when zombie reaches target_x after COB_FLY_TIME
    # zombie_x - speed * (wait_time + COB_FLY_TIME) = target_x
    # wait_time = (zombie_x - target_x) / speed - COB_FLY_TIME
    
    if zombie_speed <= 0:
        return 0.0
    
    time_to_target = (zombie_x - target_x) / zombie_speed
    wait_time = time_to_target - COB_FLY_TIME
    
    return max(0, wait_time)


# ============================================================================
# Safe Time Calculations
# ============================================================================

def get_safe_time(zombie_x: float, zombie_speed: float,
                  safe_x: float = 200) -> float:
    """
    Calculate how much time before zombie reaches danger zone
    
    Args:
        zombie_x: Current zombie x position
        zombie_speed: Zombie speed
        safe_x: X coordinate considered "dangerous" (default 200)
        
    Returns:
        Time in centiseconds until danger
    """
    return time_to_reach(zombie_x, safe_x, zombie_speed)


def get_plant_time_to_death(plant_x: float, zombie_x: float,
                            zombie_speed: float, zombie_damage: float = 100) -> float:
    """
    Calculate time until a plant would be destroyed by a zombie
    
    This is a simplified calculation assuming zombie walks directly to plant.
    
    Args:
        plant_x: Plant x position
        zombie_x: Zombie x position
        zombie_speed: Zombie speed
        zombie_damage: Damage per bite
        
    Returns:
        Time in centiseconds until plant death
    """
    time_to_reach_plant = time_to_reach(zombie_x, plant_x, zombie_speed)
    return time_to_reach_plant


# ============================================================================
# Group Prediction
# ============================================================================

def predict_group_positions(zombies: List[dict], time_cs: float) -> List[Tuple[float, int]]:
    """
    Predict positions of multiple zombies after a given time
    
    Args:
        zombies: List of zombie dicts with 'x', 'speed', 'row', 'is_slowed', 'is_frozen'
        time_cs: Time in centiseconds
        
    Returns:
        List of (predicted_x, row) tuples
    """
    predictions = []
    for z in zombies:
        pred_x = predict_position(
            z['x'], z['speed'], time_cs,
            z.get('is_slowed', False), z.get('is_frozen', False)
        )
        predictions.append((pred_x, z['row']))
    return predictions


def find_optimal_cob_target(zombies: List[dict], 
                            target_time_cs: float = COB_FLY_TIME) -> Tuple[float, int, int]:
    """
    Find optimal cob cannon target to hit the most zombies
    
    Args:
        zombies: List of zombie dicts
        target_time_cs: Time for cob to land
        
    Returns:
        (target_x, target_row, zombies_hit_count)
    """
    from data.constants import COB_EXPLODE_RADIUS
    
    if not zombies:
        return (400, 2, 0)  # Default center target
    
    # Predict positions at impact time
    predictions = predict_group_positions(zombies, target_time_cs)
    
    best_target = (400, 2, 0)
    best_count = 0
    
    # Try targeting each predicted position
    for pred_x, pred_row in predictions:
        count = 0
        for check_x, check_row in predictions:
            # Check if within cob radius and row range
            if abs(check_row - pred_row) <= 1:
                if abs(check_x - pred_x) <= COB_EXPLODE_RADIUS:
                    count += 1
        
        if count > best_count:
            best_count = count
            best_target = (pred_x, pred_row, count)
    
    return best_target
