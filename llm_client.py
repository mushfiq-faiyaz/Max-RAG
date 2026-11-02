import os
from openai import AsyncOpenAI
from httpx import Timeout
from dotenv import load_dotenv

load_dotenv()

PROVIDERS = {
    "groq_20b": {"base_url": "https://api.groq.com/openai/v1", "api_key_env": "GROQ_API_KEY", "default_model": "openai/gpt-oss-20b"},
    "groq_qwen": {"base_url": "https://api.groq.com/openai/v1", "api_key_env": "GROQ_API_KEY", "default_model": "qwen/qwen3.8-27b"},
    "groq_120b": {"base_url": "https://api.groq.com/openai/v1", "api_key_env": "GROQ_API_KEY", "default_model": "openai/gpt-oss-120b"},
    "cohere": {"base_url": "https://api.cohere.ai/compatibility/v1", "api_key_env": "COHERE_API_KEY", "default_model": "command-a-03-2025"},
    "openrouter": {"base_url": "https://openrouter.ai/api/v1", "api_key_env": "OPENROUTER_API_KEY", "default_model": "openrouter/free"}
}

FALLBACK_CHAIN = ["groq_20b", "groq_qwen", "groq_120b", "cohere", "openrouter"]

_sync_clients = {}
_stream_clients = {}

def _build_client(provider_name, read_timeout):
    config = PROVIDERS.get(provider_name)
    if not config: return None
    api_key = os.getenv(config["api_key_env"])
    if not api_key: return None
    # Use AsyncOpenAI for non-blocking calls
    return AsyncOpenAI(
        base_url=config["base_url"], 
        api_key=api_key, 
        timeout=Timeout(connect=2.0, read=read_timeout, write=2.0, pool=2.0)
    )

def _get_client(name, read_timeout):
    if name not in _sync_clients:
        _sync_clients[name] = _build_client(name, read_timeout)
    return _sync_clients[name]

def warm_up_clients():
    for p in FALLBACK_CHAIN:
        _get_client(p, read_timeout=15.0)
    print("✅ Async LLM clients pre-initialised")

async def call_llm(messages: list, max_tokens: int = 600) -> str:
    last_error = None
    for provider_name in FALLBACK_CHAIN:
        client = _get_client(provider_name, read_timeout=15.0)
        if client is None: continue
        config = PROVIDERS[provider_name]
        try:
            print(f"🤖 Trying Async LLM: {provider_name}...")
            response = await client.chat.completions.create(
                model=config["default_model"], 
                messages=messages, 
                temperature=0.1, 
                max_tokens=max_tokens
            )
            content = response.choices[0].message.content
            if content is None or len(content.strip()) == 0: 
                raise Exception("Empty response")
            return content.strip()
        except Exception as e:
            print(f"❌ {provider_name} failed: {e}")
            last_error = str(e)
            continue
    raise Exception(f"All AI models failed. Last error: {last_error}")

async def stream_llm(messages: list, max_tokens: int = 600):
    last_error = None
    for provider_name in FALLBACK_CHAIN:
        client = _get_client(provider_name, read_timeout=15.0)
        if client is None: continue
        config = PROVIDERS[provider_name]
        try:
            print(f"🌊 Streaming Async LLM: {provider_name}...")
            response = await client.chat.completions.create(
                model=config["default_model"], 
                messages=messages, 
                temperature=0.1, 
                max_tokens=max_tokens, 
                stream=True
            )
            async for chunk in response:
                if chunk.choices[0].delta.content is not None:
                    yield chunk.choices[0].delta.content
            return
        except Exception as e:
            print(f"❌ Stream failed on {provider_name}: {e}")
            last_error = str(e)
            continue
    raise Exception(f"All AI models failed to stream. Last error: {last_error}")