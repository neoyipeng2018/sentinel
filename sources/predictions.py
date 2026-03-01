"""Prediction market signal aggregator (Kalshi + Polymarket)."""

import hashlib
import json
import ssl
import urllib.request
from datetime import datetime, timezone

import certifi

from config.overrides import get_prediction_categories
from models.schemas import Signal, SignalSource

_USER_AGENT = "sentinel-risk-monitor/0.1"

# Kalshi event categories relevant to financial risk analysis
_DEFAULT_KALSHI_CATEGORIES = {
    "Economics",
    "Financials",
    "Politics",
    "Climate and Weather",
    "World",
}


def _make_ssl_context() -> ssl.SSLContext:
    """Create an SSL context using certifi's CA bundle."""
    return ssl.create_default_context(cafile=certifi.where())


def _fetch_kalshi_markets(limit: int = 50) -> list[Signal]:
    """Fetch active events/markets from Kalshi's public API."""
    signals: list[Signal] = []
    url = (
        "https://api.elections.kalshi.com/trade-api/v2/events"
        "?limit=200&status=open&with_nested_markets=true"
    )
    req = urllib.request.Request(url, headers={"User-Agent": _USER_AGENT})
    ctx = _make_ssl_context()
    try:
        with urllib.request.urlopen(req, timeout=15, context=ctx) as resp:
            data = json.loads(resp.read().decode())
    except Exception as e:
        print(f"Error fetching Kalshi events: {e}")
        return signals

    events = data.get("events", [])

    user_categories = get_prediction_categories()
    allowed = (
        {c.lower() for c in user_categories}
        if user_categories
        else {c.lower() for c in _DEFAULT_KALSHI_CATEGORIES}
    )

    # Flatten events → individual markets, filtering by category
    all_markets: list[tuple[str, dict]] = []
    for event in events:
        category = event.get("category", "")
        if category.lower() not in allowed:
            continue
        for market in event.get("markets", []):
            if market.get("status") != "active":
                continue
            all_markets.append((category, market))

    # Sort by volume descending, take top N
    all_markets.sort(key=lambda x: x[1].get("volume", 0), reverse=True)
    all_markets = all_markets[:limit]

    for category, m in all_markets:
        title = m.get("title", "")
        ticker = m.get("ticker", "")
        yes_bid = m.get("yes_bid", 0)
        yes_ask = m.get("yes_ask", 0)
        volume = m.get("volume", 0)

        # Midpoint probability (cents → fraction)
        prob = (yes_bid + yes_ask) / 200 if (yes_bid + yes_ask) else 0

        sig_id = hashlib.md5(f"kalshi:{ticker}".encode()).hexdigest()[:12]

        content = (
            f"Prediction market: {title}\n"
            f"Probability: {prob:.0%} | Volume: {volume:,} contracts\n"
            f"Platform: Kalshi | Category: {category} | Ticker: {ticker}"
        )

        signals.append(
            Signal(
                id=sig_id,
                source=SignalSource.PREDICTION_MARKET,
                title=title,
                content=content,
                url=f"https://kalshi.com/markets/{ticker}",
                timestamp=datetime.now(timezone.utc),
                metadata={
                    "platform": "kalshi",
                    "probability": round(prob, 4),
                    "volume": volume,
                    "ticker": ticker,
                    "category": category,
                },
            )
        )

    return signals


def _fetch_polymarket_markets(limit: int = 50) -> list[Signal]:
    """Fetch active markets from Polymarket's public API."""
    signals: list[Signal] = []
    url = (
        "https://gamma-api.polymarket.com/markets"
        "?limit=200&active=true&closed=false"
    )
    req = urllib.request.Request(url, headers={"User-Agent": _USER_AGENT})
    ctx = _make_ssl_context()
    try:
        with urllib.request.urlopen(req, timeout=15, context=ctx) as resp:
            data = json.loads(resp.read().decode())
    except Exception as e:
        print(f"Error fetching Polymarket markets: {e}")
        return signals

    markets = (
        data
        if isinstance(data, list)
        else data.get("markets", data.get("data", []))
    )

    # Parse volume and sort
    for m in markets:
        try:
            m["_vol"] = float(m.get("volume", 0) or 0)
        except (ValueError, TypeError):
            m["_vol"] = 0
    markets.sort(key=lambda m: m["_vol"], reverse=True)
    markets = markets[:limit]

    categories = get_prediction_categories()

    for m in markets:
        question = m.get("question", "") or m.get("title", "")
        condition_id = m.get("conditionId", "") or m.get("id", "")
        slug = m.get("slug", "")
        volume = m["_vol"]
        liquidity = float(m.get("liquidity", 0) or 0)

        if categories:
            tags = [t.lower() for t in (m.get("tags", []) or [])]
            category = (m.get("category", "") or "").lower()
            match = any(
                c.lower() in tags or c.lower() == category
                for c in categories
            )
            if not match:
                continue

        # Parse outcome prices
        outcome_prices = m.get("outcomePrices", "")
        prob = 0.0
        if isinstance(outcome_prices, str) and outcome_prices:
            try:
                prices = json.loads(outcome_prices)
                if prices:
                    prob = float(prices[0])
            except (json.JSONDecodeError, ValueError, IndexError):
                pass
        elif isinstance(outcome_prices, list) and outcome_prices:
            try:
                prob = float(outcome_prices[0])
            except (ValueError, IndexError):
                pass

        sig_id = hashlib.md5(
            f"polymarket:{condition_id}".encode()
        ).hexdigest()[:12]

        content = (
            f"Prediction market: {question}\n"
            f"Probability: {prob:.0%} | Volume: ${volume:,.0f} | "
            f"Liquidity: ${liquidity:,.0f}\n"
            f"Platform: Polymarket"
        )

        market_url = (
            f"https://polymarket.com/event/{slug}" if slug else ""
        )

        signals.append(
            Signal(
                id=sig_id,
                source=SignalSource.PREDICTION_MARKET,
                title=question,
                content=content,
                url=market_url,
                timestamp=datetime.now(timezone.utc),
                metadata={
                    "platform": "polymarket",
                    "probability": round(prob, 4),
                    "volume": volume,
                    "liquidity": liquidity,
                    "condition_id": condition_id,
                },
            )
        )

    return signals


def fetch_prediction_signals() -> list[Signal]:
    """Fetch signals from Kalshi and Polymarket prediction markets."""
    signals: list[Signal] = []
    signals.extend(_fetch_kalshi_markets())
    signals.extend(_fetch_polymarket_markets())
    return signals
