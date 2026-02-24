"""Load user overrides from config/local_config.py (git-ignored)."""

from __future__ import annotations

from typing import TYPE_CHECKING, Callable

if TYPE_CHECKING:
    from langchain_core.language_models import BaseChatModel

try:
    from config import local_config as _lc
except ImportError:
    _lc = None  # type: ignore[assignment]


def get_custom_llm_factory() -> Callable[..., "BaseChatModel"] | None:
    """Return the user-defined LLM factory, or None."""
    return getattr(_lc, "custom_llm_factory", None)


def get_watchlist() -> dict[str, list[str]] | None:
    """Return custom watchlist, or None for default."""
    return getattr(_lc, "WATCHLIST", None)


def get_z_score_threshold() -> float | None:
    """Return custom z-score threshold, or None for default."""
    return getattr(_lc, "Z_SCORE_THRESHOLD", None)


def get_subreddits() -> list[str] | None:
    """Return custom subreddit list, or None for default."""
    return getattr(_lc, "SUBREDDITS", None)


def get_news_feeds() -> list[str] | None:
    """Return custom RSS feed list, or None for default."""
    return getattr(_lc, "NEWS_FEEDS", None)


def get_custom_signals() -> Callable[[], list] | None:
    """Return the user-defined signal fetcher, or None."""
    return getattr(_lc, "custom_signals", None)


def has_custom_llm() -> bool:
    """Check whether a custom LLM factory is configured."""
    return get_custom_llm_factory() is not None
