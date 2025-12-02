"""
DeepSeek API Client

Uses OpenAI-compatible API to communicate with DeepSeek.
"""

import asyncio
from typing import Optional, List, Dict, Any, AsyncGenerator

try:
    from openai import AsyncOpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    AsyncOpenAI = None

from llm.config import LLMConfig, get_config


class DeepSeekClient:
    """
    DeepSeek API client using OpenAI compatibility.
    
    Features:
    - Async API calls
    - Streaming support with early JSON detection
    - Timeout handling
    """
    
    def __init__(self, config: Optional[LLMConfig] = None):
        """
        Initialize client.
        
        Args:
            config: LLM configuration (uses global if not provided)
        """
        if not OPENAI_AVAILABLE:
            raise ImportError(
                "openai package is required. Install with: pip install openai"
            )
        
        self.config = config or get_config()
        
        # Debug: ensure API key is set
        if not self.config.api_key:
            raise ValueError("API key is not configured! Check llm/config.py")
        
        print(f"[Client] Initializing with base_url={self.config.base_url}")
        print(f"[Client] API Key: {self.config.api_key[:10]}...{self.config.api_key[-4:]}")
        
        self.client = AsyncOpenAI(
            api_key=self.config.api_key,
            base_url=self.config.base_url
        )
    
    async def chat(self, messages: List[Dict[str, str]],
                   stream: bool = True) -> str:
        """
        Send chat request to DeepSeek.
        
        Args:
            messages: List of messages in OpenAI format
            stream: Whether to use streaming (enables early return)
            
        Returns:
            Response text from LLM
        """
        if stream:
            return await self._chat_stream(messages)
        else:
            return await self._chat_sync(messages)
    
    async def _chat_sync(self, messages: List[Dict[str, str]]) -> str:
        """Non-streaming chat request"""
        try:
            response = await asyncio.wait_for(
                self.client.chat.completions.create(
                    model=self.config.model,
                    messages=messages,
                    temperature=self.config.temperature,
                    max_tokens=self.config.max_tokens,
                    stream=False
                ),
                timeout=self.config.timeout
            )
            return response.choices[0].message.content or ""
        except asyncio.TimeoutError:
            return '{"actions": [], "plan": "API超时"}'
        except Exception as e:
            # Escape special characters in error message to prevent JSON parsing issues
            error_msg = str(e).replace('\\', '\\\\').replace('"', '\\"').replace('\n', '\\n')
            return f'{{"actions": [], "plan": "API错误: {error_msg}"}}'
    
    async def _chat_stream(self, messages: List[Dict[str, str]]) -> str:
        """
        Streaming chat request with early JSON detection.
        
        Returns as soon as a complete JSON object is detected,
        reducing latency for game responsiveness.
        """
        try:
            stream = await asyncio.wait_for(
                self.client.chat.completions.create(
                    model=self.config.model,
                    messages=messages,
                    temperature=self.config.temperature,
                    max_tokens=self.config.max_tokens,
                    stream=True
                ),
                timeout=self.config.timeout
            )
            
            collected_text = ""
            brace_count = 0
            json_started = False
            in_string = False
            escape_next = False
            
            async for chunk in stream:
                if chunk.choices and chunk.choices[0].delta.content:
                    content = chunk.choices[0].delta.content
                    collected_text += content
                    
                    # Track JSON structure for early return (with string awareness)
                    for char in content:
                        if escape_next:
                            escape_next = False
                            continue
                        
                        if char == '\\' and in_string:
                            escape_next = True
                            continue
                        
                        if char == '"' and not escape_next:
                            in_string = not in_string
                            continue
                        
                        # Only count braces outside of strings
                        if not in_string:
                            if char == "{":
                                json_started = True
                                brace_count += 1
                            elif char == "}":
                                brace_count -= 1
                                
                                # Complete JSON detected - return early
                                if json_started and brace_count == 0:
                                    return collected_text
            
            return collected_text
            
        except asyncio.TimeoutError:
            return '{"actions": [], "plan": "API超时"}'
        except Exception as e:
            # Escape special characters in error message to prevent JSON parsing issues
            error_msg = str(e).replace('\\', '\\\\').replace('"', '\\"').replace('\n', '\\n')
            return f'{{"actions": [], "plan": "API错误: {error_msg}"}}'
    
    async def chat_with_retry(self, messages: List[Dict[str, str]],
                               max_retries: int = 2) -> str:
        """
        Chat with automatic retry on failure.
        
        Args:
            messages: List of messages
            max_retries: Maximum retry attempts
            
        Returns:
            Response text
        """
        last_error = None
        
        for attempt in range(max_retries + 1):
            try:
                result = await self.chat(messages, stream=True)
                
                # Validate response has actions
                if '"actions"' in result:
                    return result
                    
            except Exception as e:
                last_error = e
                
            if attempt < max_retries:
                await asyncio.sleep(0.5)  # Brief delay before retry
        
        # Escape special characters in error message to prevent JSON parsing issues
        error_msg = str(last_error).replace('\\', '\\\\').replace('"', '\\"').replace('\n', '\\n') if last_error else "未知错误"
        return f'{{"actions": [], "plan": "多次重试失败: {error_msg}"}}'


async def create_client(api_key: Optional[str] = None) -> DeepSeekClient:
    """
    Create and return a DeepSeek client.
    
    Args:
        api_key: API key (uses config if not provided)
        
    Returns:
        Configured DeepSeek client
    """
    config = get_config()
    if api_key:
        config.api_key = api_key
    
    return DeepSeekClient(config)
