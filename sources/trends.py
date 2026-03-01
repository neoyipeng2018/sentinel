"""Google Trends signals for financial stress keywords.

Tracks search interest for terms associated with market stress, recessions,
and financial crises. Spikes in these terms often precede or coincide with
market dislocations.
"""

import hashlib
from datetime import datetime

from models.schemas import Signal, SignalSource

# Keywords grouped by theme
_STRESS_KEYWORDS = [
    "recession",
    "market crash",
    "bank run",
    "layoffs",
    "inflation",
]

_ASSET_KEYWORDS = [
    "gold price",
    "bitcoin crash",
    "housing bubble",
    "oil price",
    "dollar collapse",
]


def _make_id(*parts: str) -> str:
    raw = "".join(str(p) for p in parts) + str(datetime.utcnow().date())
    return hashlib.md5(raw.encode()).hexdigest()[:12]


def fetch_trends_signals(
    keywords: list[str] | None = None,
    timeframe: str = "today 3-m",
) -> list[Signal]:
    """Fetch Google Trends data and generate signals for spiking terms.

    Parameters
    ----------
    keywords : list of str, optional
        Terms to track. Defaults to built-in stress + asset keywords.
    timeframe : str
        Pytrends timeframe string. Default "today 3-m" (past 90 days).
    """
    from pytrends.request import TrendReq

    signals: list[Signal] = []
    if keywords is None:
        keywords = _STRESS_KEYWORDS + _ASSET_KEYWORDS

    try:
        pytrends = TrendReq(hl="en-US", tz=360, timeout=(10, 25))
    except Exception as e:
        print(f"Error initializing pytrends: {e}")
        return signals

    # Process keywords in batches of 5 (Google Trends API limit)
    for i in range(0, len(keywords), 5):
        batch = keywords[i : i + 5]
        try:
            pytrends.build_payload(batch, timeframe=timeframe, geo="US")
            df = pytrends.interest_over_time()
        except Exception as e:
            print(f"Error fetching trends for {batch}: {e}")
            continue

        if df.empty:
            continue

        # Drop the isPartial column if present
        if "isPartial" in df.columns:
            df = df.drop(columns=["isPartial"])

        for kw in batch:
            if kw not in df.columns:
                continue

            series = df[kw].dropna()
            if len(series) < 14:
                continue

            current = float(series.iloc[-1])
            avg_30d = float(series.iloc[-30:].mean()) if len(series) >= 30 else float(series.mean())
            avg_90d = float(series.mean())
            peak = float(series.max())

            # Signal if current interest is significantly above average
            if avg_30d == 0:
                continue

            ratio_vs_30d = current / avg_30d
            ratio_vs_90d = current / avg_90d if avg_90d > 0 else 1.0

            if current >= 75 and ratio_vs_30d >= 1.5:
                # Strong spike — high absolute level AND well above recent average
                signals.append(Signal(
                    id=_make_id("trends", kw),
                    source=SignalSource.GOOGLE_TRENDS,
                    title=f'Google searches for "{kw}" spiking ({current:.0f}/100)',
                    content=(
                        f'Search interest for "{kw}" is at {current:.0f}/100 (Google Trends), '
                        f"which is {ratio_vs_30d:.1f}x the 30-day average ({avg_30d:.0f}) "
                        f"and {ratio_vs_90d:.1f}x the 90-day average ({avg_90d:.0f}). "
                        f"90-day peak: {peak:.0f}/100. "
                        f"Surging search interest for financial stress terms often "
                        f"reflects growing public anxiety about economic conditions."
                    ),
                    metadata={
                        "signal_type": "search_spike",
                        "keyword": kw,
                        "current_interest": round(current),
                        "avg_30d": round(avg_30d),
                        "avg_90d": round(avg_90d),
                        "peak_90d": round(peak),
                        "ratio_vs_30d": round(ratio_vs_30d, 2),
                    },
                ))
            elif current >= 50 and ratio_vs_30d >= 2.0:
                # Moderate level but significant acceleration
                signals.append(Signal(
                    id=_make_id("trends", kw),
                    source=SignalSource.GOOGLE_TRENDS,
                    title=f'Google searches for "{kw}" rising fast ({current:.0f}/100)',
                    content=(
                        f'Search interest for "{kw}" is at {current:.0f}/100, '
                        f"{ratio_vs_30d:.1f}x its 30-day average ({avg_30d:.0f}). "
                        f"Rapid acceleration in search interest for this term may "
                        f"indicate a developing narrative gaining public attention."
                    ),
                    metadata={
                        "signal_type": "search_acceleration",
                        "keyword": kw,
                        "current_interest": round(current),
                        "avg_30d": round(avg_30d),
                        "avg_90d": round(avg_90d),
                        "ratio_vs_30d": round(ratio_vs_30d, 2),
                    },
                ))

    return signals
