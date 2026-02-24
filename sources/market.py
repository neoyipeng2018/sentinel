"""Market data fetcher using yfinance and FRED."""

import hashlib
from datetime import datetime

import pandas as pd
import yfinance as yf

from models.schemas import Signal, SignalSource

# Key tickers to monitor across asset classes
WATCHLIST = {
    "equities": ["^GSPC", "^IXIC", "^DJI", "^VIX", "^RUT"],
    "fixed_income": ["^TNX", "^TYX", "^FVX", "TLT", "HYG", "LQD"],
    "commodities": ["GC=F", "CL=F", "SI=F"],
    "fx": ["DX-Y.NYB", "EURUSD=X", "JPYUSD=X"],
    "real_estate": ["VNQ", "IYR", "XLRE"],
    "crypto": ["BTC-USD", "ETH-USD"],
}


def fetch_market_data(period: str = "1mo") -> pd.DataFrame:
    """Fetch market data for all watchlist tickers."""
    all_tickers = [t for tickers in WATCHLIST.values() for t in tickers]
    data = yf.download(all_tickers, period=period, group_by="ticker", progress=False)
    return data


def detect_anomalies(data: pd.DataFrame, z_threshold: float = 2.0) -> list[Signal]:
    """Detect unusual moves using z-score on daily returns."""
    signals: list[Signal] = []
    all_tickers = [t for tickers in WATCHLIST.values() for t in tickers]

    for ticker in all_tickers:
        try:
            if ticker in data.columns.get_level_values(0):
                close = data[ticker]["Close"].dropna()
            else:
                continue

            if len(close) < 10:
                continue

            returns = close.pct_change().dropna()
            mean = returns.rolling(20).mean().iloc[-1]
            std = returns.rolling(20).std().iloc[-1]

            if std == 0:
                continue

            latest_return = returns.iloc[-1]
            z_score = (latest_return - mean) / std

            if abs(z_score) >= z_threshold:
                direction = "surged" if z_score > 0 else "plunged"
                pct = latest_return * 100
                sig_id = hashlib.md5(
                    f"{ticker}{datetime.utcnow().date()}".encode()
                ).hexdigest()[:12]

                signals.append(
                    Signal(
                        id=sig_id,
                        source=SignalSource.MARKET_DATA,
                        title=f"{ticker} {direction} {pct:+.2f}% (z-score: {z_score:.1f})",
                        content=f"{ticker} moved {pct:+.2f}% today, which is {abs(z_score):.1f} "
                        f"standard deviations from its 20-day mean. "
                        f"Current price: ${close.iloc[-1]:.2f}",
                        timestamp=datetime.utcnow(),
                        metadata={
                            "ticker": ticker,
                            "z_score": round(z_score, 2),
                            "return_pct": round(pct, 4),
                            "price": round(close.iloc[-1], 2),
                        },
                    )
                )
        except Exception as e:
            print(f"Error processing {ticker}: {e}")

    return signals
