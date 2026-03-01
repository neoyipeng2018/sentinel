"""Prediction market signal aggregator (Kalshi + Polymarket)."""

import hashlib
import json
import urllib.request
from datetime import datetime, timezone

from config.overrides import get_prediction_categories
from models.schemas import Signal, SignalSource

_USER_AGENT = "sentinel-risk-monitor/0.1"


def _fetch_kalshi_markets(limit: int = 50) -> list[Signal]:
    """Fetch active markets from Kalshi's public API."""
    signals: list[Signal] = []
    url = (
        "https://api.elections.kalshi.com/trade-api/v2/markets"
        "?limit=200&status=open"
    )
    req = urllib.request.Request(url, headers={"User-Agent": _USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode())
    except Exception as e:
        print(f"Error fetching Kalshi markets: {e}")
        return signals

    markets = data.get("markets", [])

    # Sort by volume descending, take top N
    markets.sort(key=lambda m: m.get("volume", 0), reverse=True)
    markets = markets[:limit]

    categories = get_prediction_categories()

    for m in markets:
        title = m.get("title", "")
        ticker = m.get("ticker", "")
        yes_bid = m.get("yes_bid", 0)
        yes_ask = m.get("yes_ask", 0)
        volume = m.get("volume", 0)
        category = m.get("category", "")

        if categories and category.lower() not in [c.lower() for c in categories]:
            continue

        # Midpoint probability (cents → fraction)
        prob = (yes_bid + yes_ask) / 200 if (yes_bid + yes_ask) else 0

        sig_id = hashlib.md5(f"kalshi:{ticker}".encode()).hexdigest()[:12]

        content = (
            f"Prediction market: {title}\n"
            f"Probability: {prob:.0%} | Volume: {volume:,} contracts\n"
            f"Platform: Kalshi | Ticker: {ticker}"
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
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode())
    except Exception as e:
        print(f"Error fetching Polymarket markets: {e}")
        return signals

    markets = data if isinstance(data, list) else data.get("markets", data.get("data", []))

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

        sig_id = hashlib.md5(f"polymarket:{condition_id}".encode()).hexdigest()[:12]

        content = (
            f"Prediction market: {question}\n"
            f"Probability: {prob:.0%} | Volume: ${volume:,.0f} | "
            f"Liquidity: ${liquidity:,.0f}\n"
            f"Platform: Polymarket"
        )

        market_url = f"https://polymarket.com/event/{slug}" if slug else ""

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
