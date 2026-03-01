"""CFTC Commitments of Traders (COT) positioning signals.

Fetches weekly COT data from the CFTC website (free, no API key) and
generates signals when speculative positioning reaches extremes.

Uses two reports:
  - Traders in Financial Futures (TFF): equities, rates, FX, VIX
  - Disaggregated Futures: commodities (gold, crude, etc.)
"""

import csv
import hashlib
import io
import urllib.request
from datetime import datetime

from models.schemas import Signal, SignalSource

_TFF_URL = "https://www.cftc.gov/dea/newcot/FinFutWk.txt"
_DISAGG_URL = "https://www.cftc.gov/dea/newcot/f_disagg.txt"
_USER_AGENT = "sentinel-risk-monitor/0.1"

# Contracts to track, keyed by substring match on market name.
# Maps to a friendly name and asset class label.
_TFF_TARGETS = {
    "S&P 500 Consolidated": ("S&P 500", "equities"),
    "NASDAQ-100 Consolidated": ("Nasdaq 100", "equities"),
    "RUSSELL E-MINI": ("Russell 2000", "equities"),
    "UST 10Y NOTE": ("10Y Treasury", "rates"),
    "UST 2Y NOTE": ("2Y Treasury", "rates"),
    "UST 5Y NOTE": ("5Y Treasury", "rates"),
    "EURO FX - CHICAGO": ("Euro FX", "fx"),
    "JAPANESE YEN - CHICAGO": ("Japanese Yen", "fx"),
    "USD INDEX": ("US Dollar Index", "fx"),
    "VIX FUTURES": ("VIX Futures", "equities"),
    "FED FUNDS": ("Fed Funds", "rates"),
}

_DISAGG_TARGETS = {
    "GOLD - COMMODITY EXCHANGE": ("Gold", "commodities"),
    "SILVER - COMMODITY EXCHANGE": ("Silver", "commodities"),
    "CRUDE OIL, LIGHT SWEET - NEW YORK": ("WTI Crude", "commodities"),
    "COPPER- #1": ("Copper", "commodities"),
}


def _make_id(*parts: str) -> str:
    raw = "".join(str(p) for p in parts) + str(datetime.utcnow().date())
    return hashlib.md5(raw.encode()).hexdigest()[:12]


def _fetch_text(url: str) -> str | None:
    """Download a CFTC text file."""
    try:
        req = urllib.request.Request(url, headers={"User-Agent": _USER_AGENT})
        resp = urllib.request.urlopen(req, timeout=30)
        return resp.read().decode("utf-8", errors="replace")
    except Exception as e:
        print(f"Error fetching {url}: {e}")
        return None


def _match_target(market_name: str, targets: dict) -> tuple[str, str, str] | None:
    """Match a market name against target substrings.

    Returns (match_key, friendly_name, asset_class) or None.
    """
    for key, (name, asset) in targets.items():
        if key.lower() in market_name.lower():
            return key, name, asset
    return None


def _parse_tff(text: str) -> list[Signal]:
    """Parse Traders in Financial Futures report.

    Column layout (0-indexed):
      7  = Open Interest
      14 = Leveraged Funds Long
      15 = Leveraged Funds Short
      11 = Asset Manager Long
      12 = Asset Manager Short
    """
    signals: list[Signal] = []
    reader = csv.reader(io.StringIO(text))

    for row in reader:
        if len(row) < 22:
            continue
        market = row[0].strip().strip('"')
        match = _match_target(market, _TFF_TARGETS)
        if match is None:
            continue

        _, name, asset_class = match
        try:
            oi = int(row[7])
            lev_long = int(row[14])
            lev_short = int(row[15])
            am_long = int(row[11])
            am_short = int(row[12])
            report_date = row[2].strip()
        except (ValueError, IndexError):
            continue

        if oi == 0:
            continue

        lev_net = lev_long - lev_short
        lev_pct = lev_net / oi * 100
        am_net = am_long - am_short
        am_pct = am_net / oi * 100

        sig = _build_signal(name, asset_class, report_date, oi, lev_net, lev_pct, am_net, am_pct)
        if sig:
            signals.append(sig)

    return signals


def _parse_disagg(text: str) -> list[Signal]:
    """Parse Disaggregated Futures report.

    Column layout (0-indexed):
      7  = Open Interest
      13 = Managed Money Long
      14 = Managed Money Short
      8  = Producer/Merchant Long
      9  = Producer/Merchant Short
    """
    signals: list[Signal] = []
    reader = csv.reader(io.StringIO(text))

    for row in reader:
        if len(row) < 20:
            continue
        market = row[0].strip().strip('"')
        match = _match_target(market, _DISAGG_TARGETS)
        if match is None:
            continue

        _, name, asset_class = match
        try:
            oi = int(row[7])
            mm_long = int(row[13])
            mm_short = int(row[14])
            report_date = row[2].strip()
        except (ValueError, IndexError):
            continue

        if oi == 0:
            continue

        mm_net = mm_long - mm_short
        mm_pct = mm_net / oi * 100

        sig = _build_signal(
            name, asset_class, report_date, oi,
            spec_net=mm_net, spec_pct=mm_pct,
            am_net=None, am_pct=None,
        )
        if sig:
            signals.append(sig)

    return signals


def _build_signal(
    name: str,
    asset_class: str,
    report_date: str,
    oi: int,
    spec_net: int,
    spec_pct: float,
    am_net: int | None,
    am_pct: float | None,
) -> Signal | None:
    """Generate a signal if positioning is extreme or noteworthy."""
    # Thresholds for extreme positioning (% of OI)
    extreme_threshold = 20.0
    crowded_threshold = 35.0

    abs_pct = abs(spec_pct)
    if abs_pct < extreme_threshold:
        return None

    direction = "long" if spec_net > 0 else "short"
    severity = "extremely" if abs_pct >= crowded_threshold else "heavily"

    content_parts = [
        f"Speculative traders are {severity} net {direction} {name} futures "
        f"with a net position of {spec_net:+,} contracts ({spec_pct:+.1f}% of open interest). "
        f"Open interest: {oi:,}. Report date: {report_date}.",
    ]

    if am_net is not None and am_pct is not None:
        am_dir = "long" if am_net > 0 else "short"
        content_parts.append(
            f" Asset managers are net {am_dir} {am_net:+,} contracts ({am_pct:+.1f}% of OI)."
        )

    if abs_pct >= crowded_threshold:
        content_parts.append(
            f" Extreme crowding at {abs_pct:.1f}% of OI creates risk of a positioning squeeze "
            f"if the trade reverses."
        )

    metadata = {
        "signal_type": "cot_positioning",
        "contract": name,
        "asset_class": asset_class,
        "spec_net_contracts": spec_net,
        "spec_net_pct_oi": round(spec_pct, 1),
        "open_interest": oi,
        "report_date": report_date,
        "direction": direction,
    }
    if am_net is not None:
        metadata["asset_mgr_net_contracts"] = am_net
        metadata["asset_mgr_net_pct_oi"] = round(am_pct, 1) if am_pct is not None else None

    return Signal(
        id=_make_id("cot", name),
        source=SignalSource.COT,
        title=f"{name}: specs {severity} net {direction} ({spec_pct:+.1f}% of OI)",
        content="".join(content_parts),
        metadata=metadata,
    )


def fetch_cot_signals() -> list[Signal]:
    """Fetch CFTC COT data and generate positioning signals."""
    signals: list[Signal] = []

    tff_text = _fetch_text(_TFF_URL)
    if tff_text:
        signals.extend(_parse_tff(tff_text))

    disagg_text = _fetch_text(_DISAGG_URL)
    if disagg_text:
        signals.extend(_parse_disagg(disagg_text))

    return signals
