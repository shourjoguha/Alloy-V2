"""Test LLM connectivity and session generation."""
import asyncio
import sys
sys.path.insert(0, '/Users/shourjosmac/Documents/Gainsly')

from app.llm import get_llm_provider
from app.llm.base import LLMConfig, Message
from app.llm.ollama_provider import SESSION_PLAN_SCHEMA

async def test_health():
    """Test basic health check."""
    print("=== Testing LLM Health Check ===")
    provider = get_llm_provider()
    
    try:
        is_healthy = await provider.health_check()
        print(f"Health check result: {is_healthy}")
    except Exception as e:
        print(f"Health check error: {e}")
        import traceback
        traceback.print_exc()

async def test_simple_chat():
    """Test simple chat without JSON schema."""
    print("\n=== Testing Simple Chat ===")
    provider = get_llm_provider()
    
    try:
        messages = [Message(role="user", content="Say hello in one sentence.")]
        config = LLMConfig(model="llama3.1:8b", temperature=0.7)
        
        response = await provider.chat(messages, config)
        print(f"Response: {response.content[:100]}")
        print(f"Success!")
    except Exception as e:
        print(f"Simple chat error: {e}")
        import traceback
        traceback.print_exc()

async def test_json_schema():
    """Test chat with JSON schema."""
    print("\n=== Testing JSON Schema Chat ===")
    provider = get_llm_provider()
    
    try:
        messages = [
            Message(role="user", content='Return JSON: {"name": "test", "value": 42}')
        ]
        
        # Simple schema first
        simple_schema = {"type": "object", "properties": {"name": {"type": "string"}, "value": {"type": "number"}}}
        config = LLMConfig(model="llama3.1:8b", temperature=0.7, json_schema=simple_schema)
        
        response = await provider.chat(messages, config)
        print(f"Response content: {response.content[:200]}")
        print(f"Structured data: {response.structured_data}")
        print(f"Success!")
    except Exception as e:
        print(f"JSON schema chat error: {e}")
        import traceback
        traceback.print_exc()

async def test_session_schema():
    """Test with actual session schema."""
    print("\n=== Testing Session Schema ===")
    provider = get_llm_provider()
    
    try:
        prompt = """Generate a simple workout session with warmup and main.
Return JSON matching this structure:
{
  "warmup": [{"movement": "Jumping Jacks", "sets": 2, "reps": 10}],
  "main": [{"movement": "Squats", "sets": 3, "rep_range_min": 8, "rep_range_max": 12, "target_rpe": 7, "rest_seconds": 90}],
  "cooldown": [{"movement": "Stretching", "duration_seconds": 300}]
}
"""
        
        messages = [Message(role="user", content=prompt)]
        config = LLMConfig(
            model="llama3.1:8b",
            temperature=0.7,
            json_schema=SESSION_PLAN_SCHEMA
        )
        
        print(f"Schema keys: {list(SESSION_PLAN_SCHEMA.keys())}")
        response = await provider.chat(messages, config)
        print(f"Response length: {len(response.content)}")
        print(f"Structured data: {response.structured_data is not None}")
        if response.structured_data:
            print(f"Has warmup: {'warmup' in response.structured_data}")
            print(f"Has main: {'main' in response.structured_data}")
        print(f"Success!")
    except Exception as e:
        print(f"Session schema error: {e}")
        import traceback
        traceback.print_exc()

async def main():
    await test_health()
    await test_simple_chat()
    await test_json_schema()
    await test_session_schema()
    
    # Cleanup
    provider = get_llm_provider()
    await provider.close()

if __name__ == "__main__":
    asyncio.run(main())
