"""Risk overview dashboard page."""

import streamlit as st

from ai.chains.risk_assessor import compute_asset_risk_scores, get_top_risks
from models.schemas import AssetClass, Narrative, RiskLevel

RISK_COLORS = {
    RiskLevel.CRITICAL: "#FF1744",
    RiskLevel.HIGH: "#FF9100",
    RiskLevel.MEDIUM: "#FFEA00",
    RiskLevel.LOW: "#00E676",
}

ASSET_LABELS = {
    AssetClass.EQUITIES: "Equities",
    AssetClass.FIXED_INCOME: "Fixed Income",
    AssetClass.MACRO: "Macro",
    AssetClass.PRIVATE_MARKETS: "Private Markets",
    AssetClass.REAL_ESTATE: "Real Estate",
    AssetClass.COMMODITIES: "Commodities",

    AssetClass.FX: "FX",
}


def render_overview(narratives: list[Narrative]) -> None:
    """Render the main risk overview page."""
    st.header("Risk Overview")

    if not narratives:
        st.info("No active narratives. Click 'Refresh Signals' to fetch data.")
        return

    # Asset class risk heatmap
    scores = compute_asset_risk_scores(narratives)

    st.subheader("Risk Heatmap by Asset Class")
    cols = st.columns(4)
    for i, (asset, score) in enumerate(scores.items()):
        with cols[i % 4]:
            if score >= 7:
                color = RISK_COLORS[RiskLevel.CRITICAL]
            elif score >= 5:
                color = RISK_COLORS[RiskLevel.HIGH]
            elif score >= 3:
                color = RISK_COLORS[RiskLevel.MEDIUM]
            else:
                color = RISK_COLORS[RiskLevel.LOW]

            label = ASSET_LABELS.get(asset, asset.value)
            st.markdown(
                f"""<div style="background-color: {color}20;
                border-left: 4px solid {color};
                padding: 12px; border-radius: 4px;
                margin-bottom: 8px;">
                <div style="font-size: 0.85em; color: #888;">{label}</div>
                <div style="font-size: 1.8em; font-weight: bold;">{score}</div>
                </div>""",
                unsafe_allow_html=True,
            )

    # Top narratives
    st.subheader("Top Risk Narratives")
    top = get_top_risks(narratives, n=10)
    for nar in top:
        color = RISK_COLORS[nar.risk_level]
        assets_str = ", ".join(ASSET_LABELS.get(a, a.value) for a in nar.affected_assets)

        if nar.risk_level in [RiskLevel.CRITICAL, RiskLevel.HIGH]:
            icon = "🔴"
        elif nar.risk_level == RiskLevel.MEDIUM:
            icon = "🟡"
        else:
            icon = "🟢"
        label = f"{icon} {nar.title} — {nar.risk_level.value.upper()}"
        with st.expander(label):
            st.markdown(f"**Summary:** {nar.summary}")
            st.markdown(f"**Affected Assets:** {assets_str}")
            st.markdown(f"**Trend:** {nar.trend} | **Confidence:** {nar.confidence:.0%}")
            updated = nar.last_updated.strftime('%Y-%m-%d %H:%M')
            st.markdown(
                f"**Signals:** {len(nar.signals)}"
                f" | **Last Updated:** {updated}"
            )
