"""
Context Manager

Manages conversation history with sliding window and game summaries.
"""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from collections import deque


@dataclass
class ConversationRound:
    """A single conversation round"""
    user_message: str
    assistant_response: str
    timestamp: int  # Game clock
    wave: int


@dataclass
class GameSummary:
    """Summary of game progress"""
    wave: int
    total_waves: int
    sunflower_count: int
    attacker_count: int
    defender_count: int
    lawnmowers_remaining: int
    notes: List[str] = field(default_factory=list)


@dataclass
class FailureRecord:
    """Record of a failed action"""
    clock: int
    action_type: str
    plant_type: Optional[int]
    row: int
    col: int
    error: str


class ContextManager:
    """
    Manages LLM conversation context with:
    - Sliding window for conversation history
    - Action history tracking
    - Game summaries
    - Failure records to avoid repeated mistakes
    """
    
    def __init__(self, max_rounds: int = 6, max_actions: int = 10):
        """
        Initialize context manager.
        
        Args:
            max_rounds: Maximum conversation rounds to keep
            max_actions: Maximum action history to track
        """
        self.max_rounds = max_rounds
        self.max_actions = max_actions
        
        self.conversation_history: deque = deque(maxlen=max_rounds)
        self.action_history: deque = deque(maxlen=max_actions)
        self.failure_records: deque = deque(maxlen=20)
        
        self.game_summary: Optional[GameSummary] = None
        self.last_summary_wave: int = 0
    
    def add_round(self, user_message: str, assistant_response: str,
                  game_clock: int, wave: int) -> None:
        """Add a conversation round"""
        self.conversation_history.append(ConversationRound(
            user_message=user_message,
            assistant_response=assistant_response,
            timestamp=game_clock,
            wave=wave
        ))
    
    def add_action(self, clock: int, action_type: str,
                   plant_type: Optional[int] = None,
                   row: int = 0, col: int = 0,
                   success: bool = True, error: Optional[str] = None) -> None:
        """Add action to history"""
        action_record = {
            "t": clock,
            "a": action_type,
            "type": plant_type,
            "r": row,
            "c": col,
            "ok": success
        }
        
        if error:
            action_record["err"] = error
            self.failure_records.append(FailureRecord(
                clock=clock,
                action_type=action_type,
                plant_type=plant_type,
                row=row,
                col=col,
                error=error
            ))
        
        self.action_history.append(action_record)
    
    def update_summary(self, wave: int, total_waves: int,
                       sunflower_count: int, attacker_count: int,
                       defender_count: int, lawnmowers_remaining: int) -> None:
        """Update game summary (every 10 waves or significant change)"""
        should_update = (
            self.game_summary is None or
            wave - self.last_summary_wave >= 10 or
            wave == total_waves
        )
        
        if should_update:
            notes = []
            
            if self.game_summary:
                # Track changes
                if sunflower_count < self.game_summary.sunflower_count:
                    notes.append(f"损失向日葵{self.game_summary.sunflower_count - sunflower_count}个")
                if lawnmowers_remaining < self.game_summary.lawnmowers_remaining:
                    notes.append(f"损失小推车{self.game_summary.lawnmowers_remaining - lawnmowers_remaining}个")
            
            self.game_summary = GameSummary(
                wave=wave,
                total_waves=total_waves,
                sunflower_count=sunflower_count,
                attacker_count=attacker_count,
                defender_count=defender_count,
                lawnmowers_remaining=lawnmowers_remaining,
                notes=notes
            )
            self.last_summary_wave = wave
    
    def get_messages_for_llm(self, current_state: str,
                             system_prompt: str) -> List[Dict[str, str]]:
        """
        Build message list for LLM API call.
        
        Args:
            current_state: Current game state in YAML format
            system_prompt: System prompt to use
            
        Returns:
            List of messages in OpenAI format
        """
        messages = [{"role": "system", "content": system_prompt}]
        
        # Add game summary if available
        if self.game_summary:
            summary_text = self._format_summary()
            messages.append({"role": "system", "content": summary_text})
        
        # Add recent failure warnings
        if self.failure_records:
            failure_text = self._format_failures()
            if failure_text:
                messages.append({"role": "system", "content": failure_text})
        
        # Add conversation history
        for round_data in self.conversation_history:
            messages.append({"role": "user", "content": round_data.user_message})
            messages.append({"role": "assistant", "content": round_data.assistant_response})
        
        # Add current state
        messages.append({"role": "user", "content": current_state})
        
        return messages
    
    def _format_summary(self) -> str:
        """Format game summary for inclusion"""
        if not self.game_summary:
            return ""
        
        s = self.game_summary
        lines = [
            "# 游戏进度摘要",
            f"波次: {s.wave}/{s.total_waves}",
            f"向日葵: {s.sunflower_count}个",
            f"攻击植物: {s.attacker_count}个",
            f"防御植物: {s.defender_count}个",
            f"小推车: {s.lawnmowers_remaining}个"
        ]
        
        if s.notes:
            lines.append("注意: " + ", ".join(s.notes))
        
        return "\n".join(lines)
    
    def _format_failures(self) -> str:
        """Format recent failures as warnings"""
        if not self.failure_records:
            return ""
        
        # Get recent unique failures
        recent_failures = list(self.failure_records)[-5:]
        
        lines = ["# ⚠️ 最近失败的动作 (请避免重复)"]
        for f in recent_failures:
            lines.append(f"- {f.action_type} at ({f.row}, {f.col}): {f.error}")
        
        return "\n".join(lines)
    
    def clear(self) -> None:
        """Clear all context"""
        self.conversation_history.clear()
        self.action_history.clear()
        self.failure_records.clear()
        self.game_summary = None
        self.last_summary_wave = 0
    
    def get_recent_action_positions(self) -> List[tuple]:
        """Get positions of recent actions for deduplication"""
        return [(a["r"], a["c"]) for a in self.action_history if a.get("ok")]
