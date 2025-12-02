"""
LLM Configuration

DeepSeek API settings for the LLM game player.
Supports multiple providers: DeepSeek, SiliconFlow (硅基流动)
"""

from dataclasses import dataclass
from typing import Optional
from enum import Enum


class LLMProvider(str, Enum):
    """Supported LLM API providers"""
    DEEPSEEK = "deepseek"
    SILICONFLOW = "siliconflow"  # 硅基流动


# Provider configurations
PROVIDER_CONFIGS = {
    LLMProvider.DEEPSEEK: {
        "base_url": "https://api.deepseek.com",
        "model": "deepseek-chat",  # V3.2-Exp
        "api_key": "sk-3cd93e93115a445fb639e98930ac49ce",
    },
    LLMProvider.SILICONFLOW: {
        "base_url": "https://api.siliconflow.cn/v1",
        "model": "deepseek-ai/DeepSeek-V3",  # 或 Pro/deepseek-ai/DeepSeek-V3
        "api_key": "sk-ifhqrmcokafecbahjpukwwmgsaeueybndqnegasczpaewjgs",
    },
}


@dataclass
class LLMConfig:
    """Configuration for LLM API"""
    
    # Provider selection
    provider: LLMProvider = LLMProvider.SILICONFLOW  # 默认使用硅基流动
    
    # API Settings (默认使用硅基流动)
    api_key: str = "sk-ifhqrmcokafecbahjpukwwmgsaeueybndqnegasczpaewjgs"
    base_url: str = "https://api.siliconflow.cn/v1"
    model: str = "deepseek-ai/DeepSeek-V3"
    
    # Request settings
    temperature: float = 0.3  # Lower for more deterministic decisions
    max_tokens: int = 1024
    timeout: float = 10.0  # API timeout in seconds
    
    # Game loop settings
    # CRITICAL: llm_interval < 0.5s 会导致游戏崩溃 (Access Violation)
    # 安全范围: 0.8s - 2.0s，推荐 0.8s 作为临界值
    llm_interval: float = 0.8  # Seconds between LLM calls (0.8s = safe minimum)
    fast_loop_interval: float = 0.02  # 20ms fast loop for emergency handling
    action_cooldown: float = 0.15  # Minimum interval between plant actions (prevent crash)
    
    # Context settings
    max_history_rounds: int = 6  # Sliding window size
    max_action_history: int = 10  # Recent actions to track
    
    # Emergency thresholds
    emergency_x_threshold: int = 150  # Zombie x position for emergency
    emergency_eta_threshold: int = 200  # Time to reach home (cs)
    
    # ========================================================================
    # Latency Compensation (Time Prediction)
    # ========================================================================
    
    # Enable state prediction to compensate for LLM latency
    enable_prediction: bool = True
    
    # Estimated LLM response latency in seconds
    # This value is auto-tuned if adaptive_latency is True
    latency_seconds: float = 3.2
    
    # Enable adaptive latency measurement
    # Will automatically adjust latency_seconds based on actual response times
    adaptive_latency: bool = True
    
    # Safety margin for zombie position prediction (pixels)
    # Predicts zombies slightly closer to be conservative
    prediction_safety_margin: float = 10.0
    
    # Enable enhanced reflex layer (local rule-based responses)
    # Handles emergencies and deterministic actions without waiting for LLM
    enhanced_reflex: bool = True
    
    # Reflex layer X threshold - below this X, use local rules not LLM
    reflex_x_threshold: int = 300  # More aggressive than emergency (150)


# Global config instance
_config: Optional[LLMConfig] = None


def get_config() -> LLMConfig:
    """Get global LLM configuration"""
    global _config
    if _config is None:
        _config = LLMConfig()
    return _config


def set_config(config: LLMConfig) -> None:
    """Set global LLM configuration"""
    global _config
    _config = config


def configure_provider(config: LLMConfig, provider: LLMProvider, api_key: Optional[str] = None) -> None:
    """
    Configure LLM provider settings.
    
    Args:
        config: LLMConfig to modify
        provider: Which provider to use
        api_key: Optional API key (uses provider default if not provided)
    """
    config.provider = provider
    provider_config = PROVIDER_CONFIGS.get(provider, {})
    config.base_url = provider_config.get("base_url", config.base_url)
    config.model = provider_config.get("model", config.model)
    # Use provided API key, or fall back to provider's configured key
    if api_key:
        config.api_key = api_key
    elif "api_key" in provider_config:
        config.api_key = provider_config["api_key"]
