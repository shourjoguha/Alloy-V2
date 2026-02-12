"""OpenAI LLM provider implementation."""
import json
import logging
from typing import AsyncIterator

import httpx

from app.config.settings import get_settings
from app.llm.base import (
    LLMProvider,
    LLMConfig,
    LLMResponse,
    Message,
    StreamChunk,
)

logger = logging.getLogger(__name__)


class OpenAIProvider(LLMProvider):
    """
    OpenAI-compatible LLM provider.
    
    Works with OpenAI API, OpenRouter, and other compatible endpoints.
    Uses the chat completions endpoint for conversations.
    """
    
    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        default_model: str | None = None,
        timeout: float | None = None,
    ):
        settings = get_settings()
        self.api_key = api_key or settings.openai_api_key
        self.base_url = (base_url or settings.openai_base_url).rstrip('/')
        self.default_model = default_model or settings.openai_model
        self.timeout = timeout or settings.openai_timeout
        
        if not self.api_key:
            logger.warning("OpenAI API key not configured. LLM features will fail.")
        
        self._client: httpx.AsyncClient | None = None
    
    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create async HTTP client."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                timeout=httpx.Timeout(self.timeout),
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
            )
        return self._client
    
    async def close(self):
        """Close the HTTP client."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
    
    def _build_messages(self, messages: list[Message]) -> list[dict]:
        """Convert Message objects to OpenAI format."""
        return [{"role": m.role, "content": m.content} for m in messages]
    
    async def chat(
        self,
        messages: list[Message],
        config: LLMConfig,
    ) -> LLMResponse:
        """
        Send chat request to OpenAI-compatible API.
        
        Uses the /chat/completions endpoint with optional JSON response format.
        """
        client = await self._get_client()
        
        payload = {
            "model": config.model or self.default_model,
            "messages": self._build_messages(messages),
            "temperature": config.temperature,
        }
        
        if config.max_tokens:
            payload["max_tokens"] = config.max_tokens
        
        # Request JSON output if schema provided
        if config.json_schema:
            payload["response_format"] = {"type": "json_object"}
            # Add schema hint to system message for better compliance
            schema_hint = f"\n\nRespond with valid JSON matching this schema: {json.dumps(config.json_schema)}"
            if messages and messages[0].role == "system":
                payload["messages"][0]["content"] += schema_hint
        
        try:
            response = await client.post(
                f"{self.base_url}/chat/completions",
                json=payload,
            )
            response.raise_for_status()
        except httpx.HTTPStatusError as e:
            logger.error(f"OpenAI API error: {e.response.status_code} - {e.response.text}")
            raise
        
        data = response.json()
        content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
        
        # Parse structured data if schema was provided
        structured_data = None
        if config.json_schema:
            try:
                structured_data = json.loads(content)
            except json.JSONDecodeError:
                logger.warning("Failed to parse JSON from OpenAI response")
        
        usage = data.get("usage", {})
        
        return LLMResponse(
            content=content,
            structured_data=structured_data,
            usage={
                "prompt_tokens": usage.get("prompt_tokens"),
                "completion_tokens": usage.get("completion_tokens"),
                "total_tokens": usage.get("total_tokens"),
            },
            model=data.get("model"),
            finish_reason=data.get("choices", [{}])[0].get("finish_reason"),
        )
    
    async def chat_stream(
        self,
        messages: list[Message],
        config: LLMConfig,
    ) -> AsyncIterator[StreamChunk]:
        """
        Stream chat response from OpenAI-compatible API.
        
        Uses the /chat/completions endpoint with stream=true.
        """
        client = await self._get_client()
        
        payload = {
            "model": config.model or self.default_model,
            "messages": self._build_messages(messages),
            "temperature": config.temperature,
            "stream": True,
        }
        
        if config.max_tokens:
            payload["max_tokens"] = config.max_tokens
        
        async with client.stream(
            "POST",
            f"{self.base_url}/chat/completions",
            json=payload,
        ) as response:
            response.raise_for_status()
            
            async for line in response.aiter_lines():
                if not line or not line.startswith("data: "):
                    continue
                
                data_str = line[6:]  # Remove "data: " prefix
                
                if data_str == "[DONE]":
                    yield StreamChunk(content="", done=True)
                    break
                
                try:
                    data = json.loads(data_str)
                except json.JSONDecodeError:
                    continue
                
                delta = data.get("choices", [{}])[0].get("delta", {})
                content = delta.get("content", "")
                finish_reason = data.get("choices", [{}])[0].get("finish_reason")
                
                yield StreamChunk(
                    content=content,
                    done=finish_reason is not None,
                )
    
    async def health_check(self) -> bool:
        """
        Check if OpenAI API is accessible.
        
        Attempts to list models to verify connection.
        """
        if not self.api_key:
            return False
            
        try:
            client = await self._get_client()
            response = await client.get(f"{self.base_url}/models")
            return response.status_code == 200
        except Exception as e:
            logger.warning(f"OpenAI health check failed: {e}")
            return False
