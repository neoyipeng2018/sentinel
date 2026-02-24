"""Social media signal aggregator (Reddit)."""

import hashlib
import json
import urllib.request
from datetime import datetime

from config.overrides import get_subreddits
from models.schemas import Signal, SignalSource

# Subreddits to monitor for financial risk signals
_DEFAULT_SUBREDDITS = [
    "wallstreetbets",
    "investing",
    "economics",
    "stocks",
    "bonds",
    "RealEstate",
    "CryptoCurrency",
]

SUBREDDITS = get_subreddits() or _DEFAULT_SUBREDDITS


def fetch_reddit_signals(subreddits: list[str] | None = None, limit: int = 25) -> list[Signal]:
    """Fetch top posts from financial subreddits using Reddit's public JSON API."""
    subs = subreddits or SUBREDDITS
    signals: list[Signal] = []

    for sub in subs:
        try:
            url = f"https://www.reddit.com/r/{sub}/hot.json?limit={limit}"
            req = urllib.request.Request(url, headers={"User-Agent": "sentinel-risk-monitor/0.1"})
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode())

            for post in data.get("data", {}).get("children", []):
                p = post["data"]
                if p.get("stickied"):
                    continue

                title = p.get("title", "")
                selftext = p.get("selftext", "")[:500]
                permalink = f"https://reddit.com{p.get('permalink', '')}"
                created = datetime.utcfromtimestamp(p.get("created_utc", 0))
                score = p.get("score", 0)
                num_comments = p.get("num_comments", 0)

                sig_id = hashlib.md5(f"{title}{permalink}".encode()).hexdigest()[:12]

                signals.append(
                    Signal(
                        id=sig_id,
                        source=SignalSource.SOCIAL,
                        title=title,
                        content=selftext if selftext else title,
                        url=permalink,
                        timestamp=created,
                        metadata={
                            "subreddit": sub,
                            "score": score,
                            "num_comments": num_comments,
                            "upvote_ratio": p.get("upvote_ratio", 0),
                        },
                    )
                )
        except Exception as e:
            print(f"Error fetching r/{sub}: {e}")

    return signals
