"""RSS news feed aggregator."""

import hashlib
from datetime import datetime

import feedparser

from config.settings import settings
from models.schemas import Signal, SignalSource


def _make_id(title: str, url: str) -> str:
    return hashlib.md5(f"{title}{url}".encode()).hexdigest()[:12]


def fetch_news_signals(feed_urls: list[str] | None = None) -> list[Signal]:
    """Fetch and parse RSS feeds into Signal objects."""
    urls = feed_urls or settings.news_feeds
    signals: list[Signal] = []

    for url in urls:
        try:
            feed = feedparser.parse(url)
            for entry in feed.entries[:20]:
                title = entry.get("title", "")
                summary = entry.get("summary", entry.get("description", ""))
                link = entry.get("link", "")

                published = entry.get("published_parsed")
                if published:
                    timestamp = datetime(*published[:6])
                else:
                    timestamp = datetime.utcnow()

                signals.append(
                    Signal(
                        id=_make_id(title, link),
                        source=SignalSource.NEWS,
                        title=title,
                        content=summary,
                        url=link,
                        timestamp=timestamp,
                        metadata={"feed_url": url, "feed_title": feed.feed.get("title", "")},
                    )
                )
        except Exception as e:
            print(f"Error fetching {url}: {e}")

    return signals
