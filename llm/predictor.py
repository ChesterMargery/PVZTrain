"""
State Predictor - Time Compensation Module

Simulates game state forward in time to compensate for LLM API latency.
This is the core solution for the 3.2s delay problem.

The idea: If LLM takes 3.2s to respond, we send it the PREDICTED state 
at T+3.2s, so when the response arrives, it's actually relevant to the 
current game state.

Key predictions:
1. Zombie positions (most critical)
2. Sun production
3. Plant cooldowns
4. Wave timing
"""

import copy
from typing import Optional, List
from dataclasses import dataclass

from game.state import GameState
from game.zombie import ZombieInfo
from data.zombies import ZombieType


@dataclass
class PredictionConfig:
    """Configuration for state prediction"""
    
    # Latency to compensate (seconds)
    latency_seconds: float = 3.2
    
    # Whether to predict zombie positions
    predict_zombies: bool = True
    
    # Whether to predict sun income (DISABLED - sun needs manual collection)
    predict_sun: bool = False
    
    # Whether to predict cooldowns
    predict_cooldowns: bool = True
    
    # Safety margin for zombie position (pixels)
    # We predict slightly closer to be conservative
    safety_margin: float = 10.0
    
    # Minimum zombie X to predict to (don't predict past house)
    min_zombie_x: float = -50.0


class StatePredictor:
    """
    Predicts game state forward in time to compensate for LLM latency.
    
    Usage:
        predictor = StatePredictor(latency_seconds=3.2)
        predicted_state = predictor.predict(current_state)
        # Send predicted_state to LLM instead of current_state
    """
    
    def __init__(self, config: Optional[PredictionConfig] = None):
        """
        Initialize predictor.
        
        Args:
            config: Prediction configuration
        """
        self.config = config or PredictionConfig()
        
        # Convert to centiseconds for game time calculations
        self.latency_cs = int(self.config.latency_seconds * 100)
        
        # Track prediction accuracy for adaptive tuning
        self._prediction_history: List[dict] = []
        self._accuracy_window = 10
    
    def predict(self, state: GameState) -> GameState:
        """
        Predict game state after latency compensation time.
        
        Args:
            state: Current game state
            
        Returns:
            Predicted game state at T + latency
        """
        # Deep copy to avoid modifying actual state
        future_state = copy.deepcopy(state)
        
        # Advance game clock
        future_state.game_clock += self.latency_cs
        
        # Predict zombie positions (most critical)
        if self.config.predict_zombies:
            self._predict_zombies(future_state)
        
        # Predict sun income
        if self.config.predict_sun:
            self._predict_sun(future_state)
        
        # Predict cooldowns
        if self.config.predict_cooldowns:
            self._predict_cooldowns(future_state)
        
        return future_state
    
    def _predict_zombies(self, state: GameState) -> None:
        """
        Predict zombie positions after latency time.
        
        Zombies move left at their speed (pixels per centisecond).
        We account for:
        - Freeze/butter effects (complete stop)
        - Slow effects (50% speed)
        - Eating state (stopped)
        """
        for zombie in state.zombies:
            if zombie.hp <= 0:
                continue
            
            # Calculate effective movement time
            movement_time = self.latency_cs
            
            # Account for freeze effect
            if zombie.freeze_countdown > 0:
                if zombie.freeze_countdown >= self.latency_cs:
                    # Still frozen after latency
                    continue
                else:
                    # Will unfreeze during prediction window
                    movement_time = self.latency_cs - zombie.freeze_countdown
                    zombie.freeze_countdown = 0
            
            # Account for butter effect
            if zombie.butter_countdown > 0:
                if zombie.butter_countdown >= movement_time:
                    continue
                else:
                    movement_time -= zombie.butter_countdown
                    zombie.butter_countdown = 0
            
            # Account for slow effect
            if zombie.slow_countdown > 0:
                # Slow lasts for slow_countdown cs
                slow_time = min(zombie.slow_countdown, movement_time)
                normal_time = movement_time - slow_time
                
                # Slow = 50% speed
                movement = (zombie.speed * slow_time * 0.5) + (zombie.speed * normal_time)
                
                zombie.slow_countdown = max(0, zombie.slow_countdown - self.latency_cs)
            else:
                movement = zombie.speed * movement_time
            
            # Skip if zombie is eating (temporarily stopped)
            if zombie.is_eating:
                # Assume eating for ~100cs, then continue
                # This is a rough estimate
                movement *= 0.3  # Partial movement due to eating breaks
            
            # Apply movement (zombies move left, x decreases)
            # Add safety margin to be conservative
            zombie.x -= movement + self.config.safety_margin
            
            # Clamp to valid range
            zombie.x = max(self.config.min_zombie_x, zombie.x)
    
    def _predict_sun(self, state: GameState) -> None:
        """
        Predict sun income during latency window.
        
        Sources:
        - Sunflower: 100 sun every ~24 seconds (2400 cs)
        - Twin Sunflower: 100 sun every ~24 seconds (but counts as 2 drops)
        - Sun-shroom: 15 sun (small) then 100 sun (big)
        - Natural sun: roughly every 10 seconds in daytime
        """
        from data.plants import PlantType
        from data.offsets import SceneType
        
        predicted_sun = 0
        
        # Count sun-producing plants
        sunflower_count = 0
        twin_sunflower_count = 0
        sunshroom_count = 0
        
        for plant in state.alive_plants:
            if plant.type == PlantType.SUNFLOWER:
                sunflower_count += 1
            elif plant.type == PlantType.TWINSUNFLOWER:
                twin_sunflower_count += 1
            elif plant.type == PlantType.SUNSHROOM:
                sunshroom_count += 1
        
        # Rough sun production rate calculation
        # Sunflower: ~100 sun per 24s = 4.17 sun/s
        # In 3.2s: 4.17 * 3.2 = ~13.3 sun per sunflower
        sun_per_second = (sunflower_count * 4.17 + 
                         twin_sunflower_count * 8.34 +  # 2x production
                         sunshroom_count * 2.0)  # Smaller but faster early
        
        predicted_sun = int(sun_per_second * self.config.latency_seconds)
        
        # Natural sun in daytime levels (~10 sun per second average)
        if SceneType.is_day(state.scene):
            predicted_sun += int(10 * self.config.latency_seconds)
        
        # Add predicted sun (conservative: use 70% of prediction)
        state.sun += int(predicted_sun * 0.7)
    
    def _predict_cooldowns(self, state: GameState) -> None:
        """
        Predict cooldown reductions during latency window.
        
        All cooldowns tick down by latency time.
        """
        for seed in state.seeds:
            if seed.recharge_countdown > 0:
                seed.recharge_countdown = max(0, seed.recharge_countdown - self.latency_cs)
    
    def update_latency(self, measured_latency: float) -> None:
        """
        Update latency estimate based on actual measured values.
        Uses exponential moving average for smooth adaptation.
        
        Args:
            measured_latency: Actual measured latency in seconds
        """
        # Exponential moving average with alpha = 0.3
        alpha = 0.3
        current_latency = self.config.latency_seconds
        new_latency = alpha * measured_latency + (1 - alpha) * current_latency
        
        self.config.latency_seconds = new_latency
        self.latency_cs = int(new_latency * 100)
    
    def record_prediction(self, predicted_x: float, actual_x: float, zombie_id: int) -> None:
        """
        Record prediction accuracy for adaptive tuning.
        
        Args:
            predicted_x: Predicted zombie X position
            actual_x: Actual zombie X position when response arrived
            zombie_id: Zombie identifier
        """
        error = predicted_x - actual_x
        
        self._prediction_history.append({
            'zombie_id': zombie_id,
            'predicted_x': predicted_x,
            'actual_x': actual_x,
            'error': error
        })
        
        # Keep only recent predictions
        if len(self._prediction_history) > self._accuracy_window:
            self._prediction_history.pop(0)
        
        # Auto-adjust safety margin based on average error
        if len(self._prediction_history) >= 5:
            avg_error = sum(p['error'] for p in self._prediction_history) / len(self._prediction_history)
            # If we're consistently over-predicting, increase safety margin
            if avg_error > 20:
                self.config.safety_margin = min(50, self.config.safety_margin + 5)
            elif avg_error < -20:
                self.config.safety_margin = max(0, self.config.safety_margin - 5)
    
    def get_stats(self) -> dict:
        """Get prediction statistics"""
        if not self._prediction_history:
            return {
                'latency_seconds': self.config.latency_seconds,
                'safety_margin': self.config.safety_margin,
                'predictions_recorded': 0,
                'average_error': 0.0
            }
        
        avg_error = sum(p['error'] for p in self._prediction_history) / len(self._prediction_history)
        
        return {
            'latency_seconds': self.config.latency_seconds,
            'safety_margin': self.config.safety_margin,
            'predictions_recorded': len(self._prediction_history),
            'average_error': avg_error
        }


class AdaptivePredictor(StatePredictor):
    """
    Advanced predictor with real-time latency measurement and adaptation.
    
    Automatically measures actual LLM response time and adjusts
    prediction parameters accordingly.
    """
    
    def __init__(self, initial_latency: float = 3.0):
        super().__init__(PredictionConfig(latency_seconds=initial_latency))
        
        # Latency measurement
        self._request_timestamps: dict = {}  # request_id -> start_time
        self._latency_samples: List[float] = []
        self._max_samples = 20
    
    def start_request(self, request_id: str) -> None:
        """Mark the start of an LLM request for latency measurement"""
        import time
        self._request_timestamps[request_id] = time.time()
    
    def end_request(self, request_id: str) -> Optional[float]:
        """
        Mark the end of an LLM request and update latency estimate.
        
        Returns:
            Measured latency in seconds, or None if request not found
        """
        import time
        
        if request_id not in self._request_timestamps:
            return None
        
        start_time = self._request_timestamps.pop(request_id)
        latency = time.time() - start_time
        
        # Record sample
        self._latency_samples.append(latency)
        if len(self._latency_samples) > self._max_samples:
            self._latency_samples.pop(0)
        
        # Update predictor with new latency
        # Use 90th percentile to be conservative
        if len(self._latency_samples) >= 5:
            sorted_samples = sorted(self._latency_samples)
            p90_index = int(len(sorted_samples) * 0.9)
            p90_latency = sorted_samples[p90_index]
            self.update_latency(p90_latency)
        else:
            self.update_latency(latency)
        
        return latency
    
    def get_current_latency(self) -> float:
        """Get current latency estimate in seconds"""
        return self.config.latency_seconds
