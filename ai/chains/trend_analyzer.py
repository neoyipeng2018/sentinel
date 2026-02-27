"""Quantitative trend analysis based on narrative history snapshots."""

from models.schemas import Narrative, RiskLevel
from storage.narrative_store import get_narrative_history

RISK_LEVEL_MAP = {"low": 1, "medium": 2, "high": 3, "critical": 4}


def compute_quantitative_trend(
    narrative_id: str, current_signal_count: int
) -> str | None:
    """Compute trend from narrative history data.

    Returns 'intensifying', 'stable', or 'fading' when enough history exists,
    or None if fewer than 2 history entries (defer to LLM).
    """
    history = get_narrative_history(narrative_id)
    if len(history) < 2:
        return None

    risk_values = [
        RISK_LEVEL_MAP.get(h["risk_level"], 2) for h in history
    ]

    # 1. Risk level velocity: average of recent half vs earlier half
    mid = len(risk_values) // 2
    early_avg = sum(risk_values[:mid]) / mid if mid > 0 else risk_values[0]
    recent_avg = (
        sum(risk_values[mid:]) / len(risk_values[mid:])
        if len(risk_values[mid:]) > 0
        else risk_values[-1]
    )
    risk_velocity = (recent_avg - early_avg) / 3.0  # normalize to ~[-1, 1]

    # 2. Signal accumulation rate
    first_count = history[0].get("signal_count", 0) or 0
    last_count = history[-1].get("signal_count", 0) or current_signal_count
    if first_count > 0:
        signal_growth = (last_count - first_count) / first_count
    else:
        signal_growth = 1.0 if last_count > 0 else 0.0
    signal_score = max(-1.0, min(1.0, signal_growth))  # clamp to [-1, 1]

    # 3. Latest risk delta: difference between last two snapshots
    latest_delta = (risk_values[-1] - risk_values[-2]) / 3.0

    # Weighted combination
    score = 0.4 * risk_velocity + 0.3 * signal_score + 0.3 * latest_delta

    if score > 0.3:
        return "intensifying"
    elif score < -0.3:
        return "fading"
    return "stable"


def classify_emerging_risk(narrative: Narrative) -> bool:
    """Classify whether a narrative is an emerging risk.

    A narrative is "emerging" if ALL of:
    - Young: ≤3 history snapshots (just appeared recently)
    - Risk ≥ medium: not a low-severity blip
    - Escalating: trend is "intensifying" OR risk level ≥ high
    - Backed by evidence: ≥2 signals
    """
    history = get_narrative_history(narrative.id)
    if len(history) > 3:
        return False

    if narrative.risk_level == RiskLevel.LOW:
        return False

    is_escalating = (
        narrative.trend == "intensifying"
        or narrative.risk_level in (RiskLevel.HIGH, RiskLevel.CRITICAL)
    )
    if not is_escalating:
        return False

    if len(narrative.signals) < 2:
        return False

    return True
