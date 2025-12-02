"""
Judge Module
Provides damage judgment, collision detection, and prediction algorithms
Based on AVZ tutorial/scripts/liang_yi/judge.h
"""

from judge.collision import (
    # Basic collision detection
    is_cherry_hit,
    is_cob_hit,
    is_jalapeno_hit,
    is_doom_hit,
    is_giga_hammer,
    is_box_explode,
    is_will_be_crushed,
    # Additional collision functions
    is_cob_hit_simple,
    get_cherry_hit_range,
    get_cob_hit_range,
    get_hammer_danger_zone,
    is_pea_hit,
    get_melon_splash_targets,
    # Precise collision detection using memory offsets
    ZombieHitbox,
    PlantHitbox,
    is_zombie_hit_by_explosion,
    is_bullet_hit_zombie,
    is_zombie_attacking_plant,
    is_cob_hit_precise,
    is_cherry_hit_precise,
    calculate_collision_distance,
    get_zombie_hitbox_bounds,
    get_plant_hitbox_bounds,
)
from judge.damage import (
    calculate_cob_damage,
    calculate_cherry_damage,
    calculate_gloom_dps,
    can_kill_zombie,
)
from judge.prediction import (
    predict_position,
    time_to_reach,
    is_giga_io_dead,
    get_safe_time,
)
