"""
Response Decoder

Decodes LLM JSON responses into Action objects.
"""

import json
import re
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

from engine.action import Action, ActionType
from data.plants import PlantType, PLANT_COST

# Maximum row index (0-indexed) for pool scenes (6 rows = max index 5)
# Non-pool scenes have 5 rows (max index 4), but we use the maximum possible
# value here since we don't have scene info at decode time. The validator
# will enforce the actual scene-specific limit.
MAX_ROW_INDEX = 5  # Pool scenes have rows 0-5
MAX_COL_INDEX = 8  # All scenes have columns 0-8


@dataclass
class LLMResponse:
    """Parsed LLM response"""
    actions: List[Action]
    plan: str
    analysis: Dict[str, Any]
    raw: Dict[str, Any]


@dataclass
class ActionConditions:
    """Conditions for action execution"""
    min_sun: Optional[int] = None
    seed_ready: Optional[int] = None  # PlantType that must be ready
    cell_empty: Optional[tuple] = None  # (row, col) that must be empty


class ResponseDecoder:
    """Decodes LLM JSON responses into Action objects"""
    
    def decode(self, response_text: str) -> LLMResponse:
        """
        Decode LLM response text into actions.
        
        Args:
            response_text: Raw response text from LLM
            
        Returns:
            LLMResponse with parsed actions
        """
        # Extract JSON from response (handle markdown code blocks)
        json_str = self._extract_json(response_text)
        
        try:
            data = json.loads(json_str)
        except json.JSONDecodeError as e:
            # Debug: print what we received
            print(f"[Decoder] JSON parse error: {e}")
            print(f"[Decoder] Raw response (first 500 chars): {response_text[:500]}")
            print(f"[Decoder] Extracted JSON: {json_str[:200]}")
            # Return empty response on parse failure
            return LLMResponse(
                actions=[],
                plan="JSON解析失败",
                analysis={},
                raw={}
            )
        
        # Parse actions
        actions = self._parse_actions(data.get("actions", []))
        
        # Sort by priority (highest first)
        actions.sort(key=lambda a: a.priority, reverse=True)
        
        return LLMResponse(
            actions=actions,
            plan=data.get("plan", ""),
            analysis=data.get("analysis", {}),
            raw=data
        )
    
    def _fix_json(self, json_str: str) -> str:
        """
        Attempt to fix common JSON errors from LLM output.
        
        Common errors:
        - Missing quotes: "c: 5 -> "c": 5
        - Trailing commas: [1, 2, ] -> [1, 2]
        - Single quotes: {'a': 1} -> {"a": 1}
        """
        # Fix missing colon quote: "key: value -> "key": value
        # Pattern: "word: (not followed by ")
        fixed = re.sub(r'"(\w+):\s*([^"])', r'"\1": \2', json_str)
        
        # Fix single quotes to double quotes (outside of strings)
        fixed = fixed.replace("'", '"')
        
        # Fix trailing commas before } or ]
        fixed = re.sub(r',\s*([}\]])', r'\1', fixed)
        
        return fixed
    
    def _extract_json(self, text: str) -> str:
        """Extract JSON from response text"""
        # Try to find JSON in markdown code block
        json_match = re.search(r"```(?:json)?\s*(\{[\s\S]*?\})\s*```", text)
        if json_match:
            return self._fix_json(json_match.group(1))
        
        # Try to find raw JSON object by matching balanced braces
        # Find the first '{' and try to match to its closing '}'
        start_idx = text.find('{')
        if start_idx == -1:
            return "{}"
        
        brace_count = 0
        end_idx = start_idx
        in_string = False
        escape_next = False
        
        for i in range(start_idx, len(text)):
            char = text[i]
            
            if escape_next:
                escape_next = False
                continue
            
            if char == '\\':
                escape_next = True
                continue
            
            if char == '"' and not escape_next:
                in_string = not in_string
                continue
            
            # Only count braces outside of strings
            if not in_string:
                if char == '{':
                    brace_count += 1
                elif char == '}':
                    brace_count -= 1
                    if brace_count == 0:
                        end_idx = i
                        break
        
        if brace_count == 0 and end_idx > start_idx:
            return self._fix_json(text[start_idx:end_idx + 1])
        
        return "{}"
    
    def _parse_actions(self, action_list: List[Dict[str, Any]]) -> List[Action]:
        """Parse action list into Action objects"""
        actions = []
        
        for action_data in action_list:
            action = self._parse_single_action(action_data)
            if action:
                actions.append(action)
        
        return actions
    
    def _parse_single_action(self, data: Dict[str, Any]) -> Optional[Action]:
        """Parse a single action from dict"""
        action_type_str = data.get("a", "").lower()
        
        if action_type_str == "plant":
            return self._parse_plant_action(data)
        elif action_type_str == "shovel":
            return self._parse_shovel_action(data)
        elif action_type_str == "cob":
            return self._parse_cob_action(data)
        elif action_type_str == "wait":
            return Action.wait(reason=data.get("reason", "等待"))
        
        return None
    
    def _parse_plant_action(self, data: Dict[str, Any]) -> Optional[Action]:
        """Parse plant action"""
        plant_type = data.get("t")
        row = data.get("r")
        col = data.get("c")
        
        if plant_type is None or row is None or col is None:
            return None
        
        # Validate plant type
        try:
            plant_type = int(plant_type)
        except (ValueError, TypeError):
            return None
        
        # Validate row and col
        try:
            row = int(row)
            col = int(col)
        except (ValueError, TypeError):
            return None
        
        # Row/col bounds check using constants. The validator will enforce
        # exact scene-specific limits since we don't have scene info here.
        if not (0 <= row <= MAX_ROW_INDEX and 0 <= col <= MAX_COL_INDEX):
            return None
        
        priority = data.get("priority", 50)
        reason = data.get("reason", "")
        
        # Determine action type based on plant
        action_type = ActionType.PLANT
        if plant_type == PlantType.CHERRY_BOMB:
            action_type = ActionType.USE_CHERRY
        elif plant_type == PlantType.JALAPENO:
            action_type = ActionType.USE_JALAPENO
        elif plant_type == PlantType.ICESHROOM:
            action_type = ActionType.USE_ICE
        elif plant_type == PlantType.DOOMSHROOM:
            action_type = ActionType.USE_DOOM
        elif plant_type == PlantType.SQUASH:
            action_type = ActionType.USE_SQUASH
        
        action = Action(
            action_type=action_type,
            row=row,
            col=col,
            plant_type=plant_type,
            priority=float(priority),
            reason=reason
        )
        
        # Store conditions in metadata
        conditions = data.get("conditions", {})
        if conditions:
            action.metadata["conditions"] = conditions
        
        return action
    
    def _parse_shovel_action(self, data: Dict[str, Any]) -> Optional[Action]:
        """Parse shovel action"""
        row = data.get("r")
        col = data.get("c")
        
        if row is None or col is None:
            return None
        
        try:
            row = int(row)
            col = int(col)
        except (ValueError, TypeError):
            return None
        
        # Row/col bounds check using constants
        if not (0 <= row <= MAX_ROW_INDEX and 0 <= col <= MAX_COL_INDEX):
            return None
        
        priority = data.get("priority", 50)
        reason = data.get("reason", "")
        
        return Action.shovel(
            row=row,
            col=col,
            priority=float(priority),
            reason=reason
        )
    
    def _parse_cob_action(self, data: Dict[str, Any]) -> Optional[Action]:
        """Parse cob cannon action"""
        target_x = data.get("target_x")
        target_r = data.get("target_r", data.get("r"))
        
        if target_x is None or target_r is None:
            return None
        
        try:
            target_x = float(target_x)
            target_r = int(target_r)
        except (ValueError, TypeError):
            return None
        
        # Row bounds check using constant
        if not (0 <= target_r <= MAX_ROW_INDEX):
            return None
        
        priority = data.get("priority", 50)
        reason = data.get("reason", "")
        
        return Action.use_cob(
            target_x=target_x,
            target_row=target_r,
            priority=float(priority),
            reason=reason
        )


def decode_response(response_text: str) -> LLMResponse:
    """Convenience function to decode response"""
    decoder = ResponseDecoder()
    return decoder.decode(response_text)
