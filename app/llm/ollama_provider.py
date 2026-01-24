"""Ollama LLM provider implementation."""
import json
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


class OllamaProvider(LLMProvider):
    """
    Ollama LLM provider using the chat API.
    
    Calls POST /api/chat for multi-turn conversations with
    optional JSON schema enforcement via the format parameter.
    """
    
    def __init__(
        self,
        base_url: str | None = None,
        default_model: str | None = None,
        timeout: float | None = None,
    ):
        settings = get_settings()
        self.base_url = base_url or settings.ollama_base_url
        self.default_model = default_model or settings.ollama_model
        self.timeout = timeout or settings.ollama_timeout
        
        # Async HTTP client
        self._client: httpx.AsyncClient | None = None
    
    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create async HTTP client."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                timeout=httpx.Timeout(self.timeout),
            )
        return self._client
    
    async def close(self):
        """Close the HTTP client."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
    
    def _build_messages(self, messages: list[Message]) -> list[dict]:
        """Convert Message objects to Ollama format."""
        return [{"role": m.role, "content": m.content} for m in messages]
    
    async def chat(
        self,
        messages: list[Message],
        config: LLMConfig,
    ) -> LLMResponse:
        """
        Send chat request to Ollama.
        
        Uses the /api/chat endpoint with optional JSON format schema
        for structured output.
        """
        client = await self._get_client()
        
        payload = {
            "model": config.model or self.default_model,
            "messages": self._build_messages(messages),
            "stream": False,
            "options": {
                "temperature": config.temperature,
            },
        }
        
        # Add max tokens if specified
        if config.max_tokens:
            payload["options"]["num_predict"] = config.max_tokens
        
        # Add JSON schema for structured output
        if config.json_schema:
            payload["format"] = config.json_schema
        
        response = await client.post("/api/chat", json=payload)
        response.raise_for_status()
        
        data = response.json()
        content = data.get("message", {}).get("content", "")
        
        # Parse structured data if schema was provided
        structured_data = None
        if config.json_schema:
            try:
                structured_data = json.loads(content)
            except json.JSONDecodeError:
                # Content wasn't valid JSON, keep as raw content
                pass
        
        return LLMResponse(
            content=content,
            structured_data=structured_data,
            usage={
                "prompt_tokens": data.get("prompt_eval_count"),
                "completion_tokens": data.get("eval_count"),
                "total_duration_ns": data.get("total_duration"),
            },
            model=data.get("model"),
            finish_reason=data.get("done_reason"),
        )
    
    async def chat_stream(
        self,
        messages: list[Message],
        config: LLMConfig,
    ) -> AsyncIterator[StreamChunk]:
        """
        Stream chat response from Ollama.
        
        Uses the /api/chat endpoint with stream=true.
        """
        client = await self._get_client()
        
        payload = {
            "model": config.model or self.default_model,
            "messages": self._build_messages(messages),
            "stream": True,
            "options": {
                "temperature": config.temperature,
            },
        }
        
        if config.max_tokens:
            payload["options"]["num_predict"] = config.max_tokens
        
        # Note: Streaming with JSON format may not work well
        # as partial JSON isn't valid
        if config.json_schema:
            payload["format"] = config.json_schema
        
        async with client.stream("POST", "/api/chat", json=payload) as response:
            response.raise_for_status()
            
            async for line in response.aiter_lines():
                if not line:
                    continue
                
                try:
                    data = json.loads(line)
                except json.JSONDecodeError:
                    continue
                
                content = data.get("message", {}).get("content", "")
                done = data.get("done", False)
                
                usage = None
                if done:
                    usage = {
                        "prompt_tokens": data.get("prompt_eval_count"),
                        "completion_tokens": data.get("eval_count"),
                        "total_duration_ns": data.get("total_duration"),
                    }
                
                yield StreamChunk(
                    content=content,
                    done=done,
                    usage=usage,
                )
    
    async def health_check(self) -> bool:
        """
        Check if Ollama is running and responsive.
        
        Uses the /api/tags endpoint to verify connection.
        """
        try:
            client = await self._get_client()
            response = await client.get("/api/tags")
            return response.status_code == 200
        except Exception:
            return False
    
    async def list_models(self) -> list[dict]:
        """List available models on Ollama server."""
        client = await self._get_client()
        response = await client.get("/api/tags")
        response.raise_for_status()
        data = response.json()
        return data.get("models", [])
    
    async def model_exists(self, model_name: str) -> bool:
        """Check if a specific model is available."""
        models = await self.list_models()
        return any(m.get("name") == model_name for m in models)


# Output schemas for structured responses
SESSION_PLAN_SCHEMA = {
    "type": "object",
    "properties": {
        "warmup": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "movement": {"type": "string"},
                    "sets": {"type": "integer"},
                    "reps": {"type": "integer"},
                    "duration_seconds": {"type": "integer"},
                    "notes": {"type": "string"}
                },
                "required": ["movement"]
            }
        },
        "main": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "movement": {"type": "string"},
                    "sets": {"type": "integer"},
                    "rep_range_min": {"type": "integer"},
                    "rep_range_max": {"type": "integer"},
                    "target_rpe": {"type": "number"},
                    "rest_seconds": {"type": "integer"},
                    "superset_with": {"type": "string"},
                    "notes": {"type": "string"}
                },
                "required": ["movement", "sets"]
            }
        },
        "accessory": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "movement": {"type": "string"},
                    "sets": {"type": "integer"},
                    "rep_range_min": {"type": "integer"},
                    "rep_range_max": {"type": "integer"},
                    "target_rpe": {"type": "number"},
                    "rest_seconds": {"type": "integer"},
                    "superset_with": {"type": "string"},
                    "notes": {"type": "string"}
                },
                "required": ["movement", "sets"]
            }
        },
        "finisher": {
            "type": "object",
            "properties": {
                "type": {"type": "string"},
                "duration_minutes": {"type": "integer"},
                "exercises": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "movement": {"type": "string"},
                            "reps": {"type": "integer"},
                            "duration_seconds": {"type": "integer"}
                        }
                    }
                },
                "notes": {"type": "string"}
            }
        },
        "cooldown": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "movement": {"type": "string"},
                    "duration_seconds": {"type": "integer"},
                    "notes": {"type": "string"}
                },
                "required": ["movement"]
            }
        },
        "estimated_duration_minutes": {"type": "integer"},
        "reasoning": {"type": "string"},
        "trade_offs": {"type": "string"}
    },
    "required": ["main", "estimated_duration_minutes", "reasoning"]
}


ADAPTATION_RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {
        "adapted_plan": SESSION_PLAN_SCHEMA,
        "changes_made": {
            "type": "array",
            "items": {"type": "string"}
        },
        "reasoning": {"type": "string"},
        "trade_offs": {"type": "string"},
        "alternative_suggestion": {"type": "string"},
        "follow_up_question": {"type": "string"}
    },
    "required": ["adapted_plan", "changes_made", "reasoning"]
}
