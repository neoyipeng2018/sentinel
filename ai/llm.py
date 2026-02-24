"""LLM provider setup with OpenAI primary and Cerebras fallback."""

from langchain_cerebras import ChatCerebras
from langchain_core.language_models import BaseChatModel
from langchain_openai import ChatOpenAI

from config.settings import settings


def get_openai_llm(**kwargs) -> ChatOpenAI:
    """Get OpenAI LLM instance."""
    return ChatOpenAI(
        model=settings.openai_model,
        api_key=settings.openai_api_key,
        temperature=0.3,
        **kwargs,
    )


def get_cerebras_llm(**kwargs) -> ChatCerebras:
    """Get Cerebras LLM instance (free, fast inference)."""
    return ChatCerebras(
        model=settings.cerebras_model,
        api_key=settings.cerebras_api_key,
        temperature=0.3,
        **kwargs,
    )


def get_llm(prefer_free: bool = True, **kwargs) -> BaseChatModel:
    """Get the best available LLM.

    Uses Cerebras by default for free inference. Falls back to OpenAI.
    Set prefer_free=False to use OpenAI directly.
    """
    if prefer_free and settings.cerebras_api_key:
        try:
            return get_cerebras_llm(**kwargs)
        except Exception:
            pass

    if settings.openai_api_key:
        return get_openai_llm(**kwargs)

    raise ValueError("No LLM API key configured. Set OPENAI_API_KEY or CEREBRAS_API_KEY in .env")
