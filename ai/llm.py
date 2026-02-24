"""LLM provider setup with OpenAI primary and Cerebras fallback."""

from langchain_cerebras import ChatCerebras
from langchain_core.language_models import BaseChatModel
from langchain_openai import ChatOpenAI

from config.overrides import get_custom_llm_factory
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
    providers: list[callable] = []

    # Check for user-defined LLM in config/local_config.py
    custom_factory = get_custom_llm_factory()
    if custom_factory is not None:
        providers.append(custom_factory)

    if prefer_free and settings.cerebras_api_key:
        providers.append(get_cerebras_llm)
    if settings.openai_api_key:
        providers.append(get_openai_llm)
    if not prefer_free and settings.cerebras_api_key:
        providers.append(get_cerebras_llm)

    if not providers:
        raise ValueError(
            "No LLM API key configured. Set OPENAI_API_KEY or CEREBRAS_API_KEY in .env"
        )

    return _LLMWithFallback(providers=providers, provider_kwargs=kwargs)


class _LLMWithFallback(BaseChatModel):
    """Wrapper that tries providers in order, falling back on errors."""

    providers: list = []
    provider_kwargs: dict = {}
    _current: BaseChatModel | None = None

    class Config:
        arbitrary_types_allowed = True

    @property
    def _llm_type(self) -> str:
        return "fallback"

    def _generate(self, messages, stop=None, run_manager=None, **kwargs):
        errors = []
        for factory in self.providers:
            try:
                llm = factory(**self.provider_kwargs)
                result = llm._generate(
                    messages, stop=stop, run_manager=run_manager, **kwargs
                )
                self._current = llm
                return result
            except Exception as e:
                errors.append(e)
                continue
        raise errors[-1]
