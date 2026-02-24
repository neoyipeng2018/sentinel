"""Assess and score risk across asset classes from active narratives."""

from models.schemas import AssetClass, Narrative, RiskLevel

# Numeric weights for risk levels
RISK_WEIGHTS = {
    RiskLevel.CRITICAL: 4,
    RiskLevel.HIGH: 3,
    RiskLevel.MEDIUM: 2,
    RiskLevel.LOW: 1,
}


def compute_asset_risk_scores(narratives: list[Narrative]) -> dict[AssetClass, float]:
    """Compute a composite risk score (0-10) for each asset class based on active narratives."""
    scores: dict[AssetClass, float] = {ac: 0.0 for ac in AssetClass}
    counts: dict[AssetClass, int] = {ac: 0 for ac in AssetClass}

    for narrative in narratives:
        weight = RISK_WEIGHTS.get(narrative.risk_level, 1)
        trend_multiplier = {"intensifying": 1.5, "stable": 1.0, "fading": 0.5}.get(
            narrative.trend, 1.0
        )
        score = weight * trend_multiplier * narrative.confidence

        for asset in narrative.affected_assets:
            scores[asset] += score
            counts[asset] += 1

    # Normalize to 0-10 scale
    max_score = max(scores.values()) if any(scores.values()) else 1
    return {ac: round((s / max_score) * 10, 1) if max_score > 0 else 0 for ac, s in scores.items()}


def get_top_risks(narratives: list[Narrative], n: int = 5) -> list[Narrative]:
    """Get the top N narratives by risk severity."""

    def risk_sort_key(nar: Narrative) -> float:
        weight = RISK_WEIGHTS.get(nar.risk_level, 1)
        trend_mult = {"intensifying": 1.5, "stable": 1.0, "fading": 0.5}.get(nar.trend, 1.0)
        return weight * trend_mult * nar.confidence

    return sorted(narratives, key=risk_sort_key, reverse=True)[:n]
