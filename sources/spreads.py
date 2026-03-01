"""Bond/credit spread and VIX term structure signals.

Computes derived indicators from market data that signal stress before
individual price moves become anomalies:
  - VIX term structure (backwardation = near-term fear)
  - HYG/LQD ratio (credit spread proxy)
  - 10Y-3M treasury spread (yield curve shape)
"""

import hashlib
from datetime import datetime

import pandas as pd
import yfinance as yf

from models.schemas import Signal, SignalSource

_SPREAD_TICKERS = [
    "^VIX",    # VIX spot
    "^VIX3M",  # VIX 3-month
    "^TNX",    # 10Y treasury yield
    "^FVX",    # 5Y treasury yield
    "^TYX",    # 30Y treasury yield
    "^IRX",    # 13-week T-bill rate
    "HYG",     # High-yield corporate bond ETF
    "LQD",     # Investment-grade corporate bond ETF
]


def _make_id(*parts: str) -> str:
    raw = "".join(str(p) for p in parts) + str(datetime.utcnow().date())
    return hashlib.md5(raw.encode()).hexdigest()[:12]


def _get_close(data: pd.DataFrame, ticker: str) -> pd.Series | None:
    """Safely extract close prices for a ticker."""
    try:
        if ticker in data.columns.get_level_values(0):
            series = data[ticker]["Close"].dropna()
            if len(series) >= 5:
                return series
    except Exception:
        pass
    return None


def fetch_spread_signals(period: str = "3mo") -> list[Signal]:
    """Compute spread-based signals from market data."""
    signals: list[Signal] = []
    try:
        data = yf.download(
            _SPREAD_TICKERS, period=period, group_by="ticker", progress=False
        )
    except Exception as e:
        print(f"Error fetching spread data: {e}")
        return signals

    signals.extend(_vix_term_structure(data))
    signals.extend(_credit_spread(data))
    signals.extend(_yield_curve(data))
    return signals


# ── VIX term structure ──────────────────────────────────────────────


def _vix_term_structure(data: pd.DataFrame) -> list[Signal]:
    """VIX spot vs VIX3M — backwardation signals near-term fear."""
    signals: list[Signal] = []
    vix = _get_close(data, "^VIX")
    vix3m = _get_close(data, "^VIX3M")
    if vix is None or vix3m is None:
        return signals

    common = vix.index.intersection(vix3m.index)
    if len(common) < 20:
        return signals

    vix_now = float(vix.loc[common].iloc[-1])
    vix3m_now = float(vix3m.loc[common].iloc[-1])
    if vix3m_now == 0:
        return signals

    ratio = vix_now / vix3m_now
    ratio_series = vix.loc[common] / vix3m.loc[common]
    ratio_20d = float(ratio_series.rolling(20).mean().iloc[-1])

    if ratio > 1.05:
        severity = "significant" if ratio > 1.15 else "moderate"
        signals.append(Signal(
            id=_make_id("vix_term"),
            source=SignalSource.MARKET_DATA,
            title=f"VIX term structure in backwardation (ratio: {ratio:.2f})",
            content=(
                f"VIX spot ({vix_now:.1f}) is trading above VIX3M ({vix3m_now:.1f}), "
                f"ratio {ratio:.2f}. This indicates {severity} near-term fear exceeding "
                f"longer-term expectations. 20-day avg ratio: {ratio_20d:.2f}. "
                f"Backwardation historically signals elevated short-term risk."
            ),
            metadata={
                "signal_type": "vix_term_structure",
                "vix_spot": round(vix_now, 2),
                "vix3m": round(vix3m_now, 2),
                "ratio": round(ratio, 3),
                "ratio_20d_avg": round(ratio_20d, 3),
                "state": "backwardation",
            },
        ))
    elif ratio < 0.85:
        signals.append(Signal(
            id=_make_id("vix_term"),
            source=SignalSource.MARKET_DATA,
            title=f"VIX term structure in deep contango (ratio: {ratio:.2f})",
            content=(
                f"VIX spot ({vix_now:.1f}) is well below VIX3M ({vix3m_now:.1f}), "
                f"ratio {ratio:.2f}. Deep contango may indicate market complacency. "
                f"20-day avg ratio: {ratio_20d:.2f}."
            ),
            metadata={
                "signal_type": "vix_term_structure",
                "vix_spot": round(vix_now, 2),
                "vix3m": round(vix3m_now, 2),
                "ratio": round(ratio, 3),
                "ratio_20d_avg": round(ratio_20d, 3),
                "state": "deep_contango",
            },
        ))

    if vix_now > 25:
        level = "extremely elevated" if vix_now > 35 else "elevated"
        signals.append(Signal(
            id=_make_id("vix_level"),
            source=SignalSource.MARKET_DATA,
            title=f"VIX {level} at {vix_now:.1f}",
            content=(
                f"The VIX is at {vix_now:.1f}, which is {level}. "
                f"VIX above 25 indicates significant market stress. "
                f"VIX3M at {vix3m_now:.1f}."
            ),
            metadata={
                "signal_type": "vix_level",
                "vix_spot": round(vix_now, 2),
                "level": level,
            },
        ))

    return signals


# ── Credit spread ───────────────────────────────────────────────────


def _credit_spread(data: pd.DataFrame) -> list[Signal]:
    """HYG/LQD ratio as a credit spread proxy — falling ratio = widening."""
    signals: list[Signal] = []
    hyg = _get_close(data, "HYG")
    lqd = _get_close(data, "LQD")
    if hyg is None or lqd is None:
        return signals

    common = hyg.index.intersection(lqd.index)
    if len(common) < 20:
        return signals

    ratio = hyg.loc[common] / lqd.loc[common]
    ratio_now = float(ratio.iloc[-1])
    ratio_20d = float(ratio.rolling(20).mean().iloc[-1])
    ratio_std = float(ratio.rolling(20).std().iloc[-1])

    if ratio_std == 0:
        return signals

    z = (ratio_now - ratio_20d) / ratio_std

    if z < -1.5:
        severity = "sharply" if z < -2.5 else "notably"
        signals.append(Signal(
            id=_make_id("credit_spread"),
            source=SignalSource.MARKET_DATA,
            title=f"Credit spreads {severity} widening (HYG/LQD z: {z:.1f})",
            content=(
                f"High-yield bonds (HYG) are underperforming investment grade (LQD) — "
                f"HYG/LQD ratio z-score {z:.1f}. "
                f"Current ratio: {ratio_now:.4f}, 20-day avg: {ratio_20d:.4f}. "
                f"Widening credit spreads signal deteriorating risk appetite "
                f"and often precede broader equity weakness."
            ),
            metadata={
                "signal_type": "credit_spread",
                "hyg_lqd_ratio": round(ratio_now, 4),
                "ratio_20d_avg": round(ratio_20d, 4),
                "z_score": round(z, 2),
                "direction": "widening",
            },
        ))
    elif z > 2.0:
        signals.append(Signal(
            id=_make_id("credit_spread"),
            source=SignalSource.MARKET_DATA,
            title=f"Credit spreads tightening sharply (HYG/LQD z: {z:.1f})",
            content=(
                f"High-yield bonds (HYG) are outperforming investment grade (LQD) — "
                f"HYG/LQD ratio z-score {z:.1f}. "
                f"Current ratio: {ratio_now:.4f}, 20-day avg: {ratio_20d:.4f}. "
                f"Tightening credit spreads indicate improving risk appetite."
            ),
            metadata={
                "signal_type": "credit_spread",
                "hyg_lqd_ratio": round(ratio_now, 4),
                "ratio_20d_avg": round(ratio_20d, 4),
                "z_score": round(z, 2),
                "direction": "tightening",
            },
        ))

    return signals


# ── Yield curve ─────────────────────────────────────────────────────


def _yield_curve(data: pd.DataFrame) -> list[Signal]:
    """10Y-3M treasury spread — classic recession indicator."""
    signals: list[Signal] = []
    tnx = _get_close(data, "^TNX")  # 10Y yield
    irx = _get_close(data, "^IRX")  # 3M yield

    if tnx is None or irx is None:
        return signals

    common = tnx.index.intersection(irx.index)
    if len(common) < 10:
        return signals

    spread = tnx.loc[common] - irx.loc[common]
    current = float(spread.iloc[-1])
    prev_5d = float(spread.iloc[-5]) if len(spread) >= 5 else current
    change = current - prev_5d

    if current < 0:
        signals.append(Signal(
            id=_make_id("yc_10y3m"),
            source=SignalSource.MARKET_DATA,
            title=f"Yield curve inverted: 10Y-3M at {current:.2f}%",
            content=(
                f"The 10Y-3M treasury spread is {current:.2f}%, inverted. "
                f"5-day change: {change:+.2f}%. "
                f"10Y: {float(tnx.loc[common].iloc[-1]):.2f}%, "
                f"3M: {float(irx.loc[common].iloc[-1]):.2f}%. "
                f"An inverted 10Y-3M curve has preceded every US recession "
                f"since the 1960s (6-24 month lead)."
            ),
            metadata={
                "signal_type": "yield_curve",
                "spread": "10Y-3M",
                "value": round(current, 3),
                "change_5d": round(change, 3),
                "state": "inverted",
            },
        ))
    elif current < 0.5:
        signals.append(Signal(
            id=_make_id("yc_10y3m"),
            source=SignalSource.MARKET_DATA,
            title=f"Yield curve near flat: 10Y-3M at {current:.2f}%",
            content=(
                f"The 10Y-3M treasury spread is {current:.2f}%, near flat. "
                f"5-day change: {change:+.2f}%. "
                f"A flat curve signals slowing growth expectations."
            ),
            metadata={
                "signal_type": "yield_curve",
                "spread": "10Y-3M",
                "value": round(current, 3),
                "change_5d": round(change, 3),
                "state": "flat",
            },
        ))

    if abs(change) > 0.20:
        direction = "steepening" if change > 0 else "flattening"
        signals.append(Signal(
            id=_make_id("yc_10y3m_move"),
            source=SignalSource.MARKET_DATA,
            title=f"Yield curve rapidly {direction}: 10Y-3M moved {change:+.2f}% in 5d",
            content=(
                f"The 10Y-3M spread moved {change:+.2f}% over 5 days "
                f"(from {prev_5d:.2f}% to {current:.2f}%). "
                f"Rapid {direction} signals shifting rate expectations."
            ),
            metadata={
                "signal_type": "yield_curve_move",
                "spread": "10Y-3M",
                "value": round(current, 3),
                "change_5d": round(change, 3),
                "direction": direction,
            },
        ))

    return signals
