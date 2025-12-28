"""
LLM client abstraction for swapping providers (OpenAI/Gemini/Claude).

"""

import os
from typing import Optional
from langchain_openai import ChatOpenAI
from langchain_core.language_models import BaseChatModel

# TODO: Add Gemini/Claude support when needed
# from langchain_google_genai import ChatGoogleGenerativeAI
# from langchain_anthropic import ChatAnthropic

def get_llm(
    provider: str = "openai",
    model_name: Optional[str] = None,
    temperature: float = 0.0
) -> BaseChatModel:
    """
    Get LLM client for specified provider.

    Pattern adapted from day_12/langgraph_agent_lib/models.py

    Args:
        provider: "openai", "gemini", or "claude" (future)
        model_name: Override default model name
        temperature: Model temperature

    Returns:
        Langchain chat model instance
    """
    provider = provider.lower()

    if provider == "openai":
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY environment variable not set")
        
        model = model_name or os.getenv("OPENAI_CHAT_MODEL", "gpt-4o-mini")
        return ChatOpenAI(model=model, temperature=temperature, api_key=api_key)

    # Future: Add Gemini/Claude support
    # elif provider == "gemini":
    #   ...
    # elif provider == "claude":
    #   ...

    else:
        raise ValueError(f"Unsupported provider: {provider}")

# LLM response caching
def setup_llm_cache(cache_type: str = "memory", cache_path: Optional[str] = None):
    """
    Setup LLM response caching.

    Args:
        cache_type: "memory" (dev) or "sqlite" (production)
        cache_path: Path for SQLite cache file (optional)
    """
    from langchain_core.caches import InMemoryCache
    from langchain_community.cache import SQLiteCache
    from langchain_core.globals import set_llm_cache

    if cache_type == "memory":
        set_llm_cache(InMemoryCache())
    elif cache_type == "sqlite":
        db_path = cache_path or "./cache/llm_cache.db"
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        set_llm_cache(SQLiteCache(database_path=db_path))
    else:
        raise ValueError(f"Unsupported cache_type: {cache_type}")
