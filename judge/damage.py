"""
Damage Calculation Module
Calculates damage values and determines kill conditions
"""

from typing import Optional, List
from data.constants import (
    CHERRY_DAMAGE,
    JALAPENO_DAMAGE,
    DOOM_DAMAGE,
    DOOM_DAMAGE_GARG,
    PEA_DAMAGE,
    FIRE_PEA_DAMAGE,
    MELON_DAMAGE,
    GLOOM_DAMAGE_PER_CS,
)
from data.zombies import (
    ZombieType,
    get_zombie_total_hp,
    is_gargantuar,
    GARGANTUAR_ZOMBIES,
)


# ============================================================================
# Instant Kill Damage
# ============================================================================

def calculate_cherry_damage(zombie_type: int) -> int:
    """
    Calculate damage dealt by cherry bomb to a zombie
    
    Cherry bomb deals 1800 damage, but Gargantuars take half damage.
    
    Args:
        zombie_type: Type of zombie
        
    Returns:
        Damage amount
    """
    if is_gargantuar(zombie_type):
        return CHERRY_DAMAGE // 2  # 900 to Gargs
    return CHERRY_DAMAGE


def calculate_jalapeno_damage(zombie_type: int) -> int:
    """
    Calculate damage dealt by jalapeno to a zombie
    
    Jalapeno deals 1800 damage, Gargantuars take half.
    
    Args:
        zombie_type: Type of zombie
        
    Returns:
        Damage amount
    """
    if is_gargantuar(zombie_type):
        return JALAPENO_DAMAGE // 2
    return JALAPENO_DAMAGE


def calculate_doom_damage(zombie_type: int) -> int:
    """
    Calculate damage dealt by doom-shroom to a zombie
    
    Doom-shroom deals 1800 damage, Gargantuars take half.
    
    Args:
        zombie_type: Type of zombie
        
    Returns:
        Damage amount
    """
    if is_gargantuar(zombie_type):
        return DOOM_DAMAGE_GARG
    return DOOM_DAMAGE


def calculate_cob_damage(zombie_type: int) -> int:
    """
    Calculate damage dealt by cob cannon to a zombie
    
    Cob cannon deals 1800 damage, Gargantuars take half.
    
    Args:
        zombie_type: Type of zombie
        
    Returns:
        Damage amount
    """
    # Cob cannon damage same as other instant kills
    if is_gargantuar(zombie_type):
        return 900
    return 1800


# ============================================================================
# DPS Calculations
# ============================================================================

def calculate_gloom_dps() -> float:
    """
    Calculate Gloom-shroom DPS (damage per centisecond)
    
    Gloom-shroom deals 80 damage every 200cs to all zombies in range.
    
    Returns:
        DPS value (hp per cs)
    """
    return GLOOM_DAMAGE_PER_CS  # 0.4 hp/cs


def calculate_pea_dps(has_torchwood: bool = False) -> float:
    """
    Calculate Peashooter DPS
    
    Peashooter deals 20 damage per shot, fires every 141cs.
    Fire pea (through torchwood) deals 40 damage.
    
    Args:
        has_torchwood: Whether pea passes through torchwood
        
    Returns:
        DPS value (hp per cs)
    """
    damage = FIRE_PEA_DAMAGE if has_torchwood else PEA_DAMAGE
    attack_interval = 141  # cs
    return damage / attack_interval


def calculate_repeater_dps(has_torchwood: bool = False) -> float:
    """
    Calculate Repeater DPS (2 peas per shot)
    """
    return calculate_pea_dps(has_torchwood) * 2


def calculate_gatling_dps(has_torchwood: bool = False) -> float:
    """
    Calculate Gatling Pea DPS (4 peas per shot)
    """
    return calculate_pea_dps(has_torchwood) * 4


def calculate_melon_dps() -> float:
    """
    Calculate Melon-pult DPS
    
    Melon deals 80 direct damage + splash, fires every ~300cs.
    """
    return MELON_DAMAGE / 300


# ============================================================================
# Kill Condition Checks
# ============================================================================

def can_kill_zombie(zombie_hp: int, zombie_type: int, 
                    damage_source: str) -> bool:
    """
    Check if a damage source can kill a zombie
    
    Args:
        zombie_hp: Current zombie HP
        zombie_type: Zombie type ID
        damage_source: Type of damage ('cherry', 'cob', 'jalapeno', 'doom')
        
    Returns:
        True if zombie would be killed
    """
    damage_funcs = {
        'cherry': calculate_cherry_damage,
        'cob': calculate_cob_damage,
        'jalapeno': calculate_jalapeno_damage,
        'doom': calculate_doom_damage,
    }
    
    damage_func = damage_funcs.get(damage_source)
    if not damage_func:
        return False
    
    damage = damage_func(zombie_type)
    return damage >= zombie_hp


def cobs_needed_to_kill(zombie_hp: int, zombie_type: int) -> int:
    """
    Calculate number of cob cannon hits needed to kill a zombie
    
    Args:
        zombie_hp: Current zombie HP
        zombie_type: Zombie type ID
        
    Returns:
        Number of cob hits needed
    """
    damage_per_cob = calculate_cob_damage(zombie_type)
    if damage_per_cob <= 0:
        return float('inf')
    
    import math
    return math.ceil(zombie_hp / damage_per_cob)


def time_to_kill_with_gloom(zombie_hp: int, num_glooms: int = 1) -> float:
    """
    Calculate time (cs) to kill a zombie with Gloom-shrooms
    
    Args:
        zombie_hp: Current zombie HP
        num_glooms: Number of Gloom-shrooms hitting the zombie
        
    Returns:
        Time in centiseconds
    """
    dps = GLOOM_DAMAGE_PER_CS * num_glooms
    if dps <= 0:
        return float('inf')
    return zombie_hp / dps


# ============================================================================
# Overkill Analysis
# ============================================================================

def calculate_overkill(zombie_hp: int, zombie_type: int,
                       damage_source: str) -> int:
    """
    Calculate wasted damage (overkill) for a given attack
    
    Args:
        zombie_hp: Current zombie HP
        zombie_type: Zombie type ID
        damage_source: Type of damage
        
    Returns:
        Overkill damage (negative if not killed)
    """
    damage_funcs = {
        'cherry': calculate_cherry_damage,
        'cob': calculate_cob_damage,
        'jalapeno': calculate_jalapeno_damage,
        'doom': calculate_doom_damage,
    }
    
    damage_func = damage_funcs.get(damage_source)
    if not damage_func:
        return 0
    
    damage = damage_func(zombie_type)
    return damage - zombie_hp


def calculate_total_damage_needed(zombies: List[tuple]) -> int:
    """
    Calculate total damage needed to kill a group of zombies
    
    Args:
        zombies: List of (hp, type) tuples
        
    Returns:
        Total damage needed
    """
    return sum(hp for hp, _ in zombies)


def calculate_cob_efficiency(zombies_hit: List[tuple]) -> float:
    """
    Calculate efficiency of a cob cannon hit
    
    Efficiency = total damage dealt / potential damage wasted
    
    Args:
        zombies_hit: List of (hp, type) tuples of zombies hit
        
    Returns:
        Efficiency score (higher is better)
    """
    if not zombies_hit:
        return 0.0
    
    total_hp = sum(hp for hp, _ in zombies_hit)
    total_damage = sum(calculate_cob_damage(ztype) for _, ztype in zombies_hit)
    
    if total_damage <= 0:
        return 0.0
    
    # Efficiency is ratio of useful damage to total damage
    useful_damage = min(total_hp, total_damage)
    return useful_damage / 1800  # Normalize to single cob damage
