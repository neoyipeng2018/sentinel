"""Risk overview dashboard page."""

import math

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
    AssetClass.PRIVATE_MARKETS: "Private Mkts",
    AssetClass.REAL_ESTATE: "Real Estate",
    AssetClass.COMMODITIES: "Commodities",
    AssetClass.FX: "FX",
}

TREND_DISPLAY = {
    "intensifying": ("&#9650;", "trend-up"),     # ▲
    "stable": ("&#9654;", "trend-stable"),        # ▶
    "fading": ("&#9660;", "trend-down"),          # ▼
}


def _svg_gauge(score: float, max_score: float, color: str, size: int = 80) -> str:
    """Generate an SVG arc gauge for a risk score."""
    radius = 32
    cx, cy = size // 2, size // 2
    stroke_width = 6
    circumference = 2 * math.pi * radius
    # Arc from 0.75 turn (bottom-left) through top to 0.25 turn (bottom-right) = 0.75 of circle
    arc_length = circumference * 0.75
    filled = arc_length * (score / max_score) if max_score > 0 else 0
    gap = arc_length - filled

    return f"""<svg width="{size}" height="{size}" viewBox="0 0 {size} {size}">
  <circle cx="{cx}" cy="{cy}" r="{radius}" fill="none"
    stroke="#1a2332" stroke-width="{stroke_width}"
    stroke-dasharray="{arc_length} {circumference - arc_length}"
    stroke-dashoffset="{-circumference * 0.125}"
    stroke-linecap="round"/>
  <circle cx="{cx}" cy="{cy}" r="{radius}" fill="none"
    stroke="{color}" stroke-width="{stroke_width}"
    stroke-dasharray="{filled} {gap + circumference - arc_length}"
    stroke-dashoffset="{-circumference * 0.125}"
    stroke-linecap="round"/>
  <text x="{cx}" y="{cy + 4}" text-anchor="middle"
    fill="{color}" font-size="16" font-weight="700"
    font-family="SF Mono, Consolas, monospace">{score:.0f}</text>
</svg>"""


def render_overview(narratives: list[Narrative]) -> None:
    """Render the main risk overview page."""
    st.markdown(
        '<div class="section-header">'
        '<span class="pulse-dot"></span> RISK OVERVIEW'
        "</div>",
        unsafe_allow_html=True,
    )

    if not narratives:
        st.markdown(
            '<div class="cmd-panel" style="text-align: center; color: #4a5568;">'
            "No active narratives. Click REFRESH SIGNALS to fetch data."
            "</div>",
            unsafe_allow_html=True,
        )
        return

    # Asset class risk heatmap
    scores = compute_asset_risk_scores(narratives)

    st.markdown(
        '<div class="section-header">RISK HEATMAP BY ASSET CLASS</div>',
        unsafe_allow_html=True,
    )
    cols = st.columns(min(len(scores), 4))
    for i, (asset, score) in enumerate(scores.items()):
        with cols[i % min(len(scores), 4)]:
            if score >= 7:
                color = RISK_COLORS[RiskLevel.CRITICAL]
                level_cls = "critical"
            elif score >= 5:
                color = RISK_COLORS[RiskLevel.HIGH]
                level_cls = "high"
            elif score >= 3:
                color = RISK_COLORS[RiskLevel.MEDIUM]
                level_cls = "medium"
            else:
                color = RISK_COLORS[RiskLevel.LOW]
                level_cls = "low"

            label = ASSET_LABELS.get(asset, asset.value)
            gauge_svg = _svg_gauge(score, 10, color)
            glow = " glow-critical" if level_cls == "critical" else ""

            st.markdown(
                f'<div class="cmd-panel cmd-panel-{level_cls}{glow}">'
                f'<div class="gauge-container">'
                f"{gauge_svg}"
                f'<div class="gauge-label">{label}</div>'
                f"</div></div>",
                unsafe_allow_html=True,
            )

    # Top narratives
    st.markdown(
        '<div class="section-header" style="margin-top: 16px;">'
        "TOP RISK NARRATIVES</div>",
        unsafe_allow_html=True,
    )

    top = get_top_risks(narratives, n=10)
    for nar in top:
        color = RISK_COLORS[nar.risk_level]
        level = nar.risk_level.value
        assets_str = ", ".join(
            ASSET_LABELS.get(a, a.value) for a in nar.affected_assets
        )

        trend_arrow, trend_cls = TREND_DISPLAY.get(
            nar.trend, ("&#9654;", "trend-stable")
        )

        glow = " glow-critical" if nar.risk_level == RiskLevel.CRITICAL else ""
        updated = nar.last_updated.strftime("%Y-%m-%d %H:%M")

        st.markdown(
            f'<div class="cmd-panel cmd-panel-{level}{glow}">'
            f'<div style="display: flex; justify-content: space-between; '
            f'align-items: flex-start; gap: 12px;">'
            f"<div style=\"flex: 1;\">"
            f'<div style="display: flex; align-items: center; gap: 8px; '
            f'margin-bottom: 6px;">'
            f'<span class="badge badge-{level}">{level}</span>'
            f'<span style="font-weight: 600; color: #e0e4ec; font-size: 0.9rem;">'
            f"{nar.title}</span>"
            f"</div>"
            f'<div style="color: #8892a4; font-size: 0.8rem; line-height: 1.5; '
            f'margin-bottom: 6px;">{nar.summary}</div>'
            f'<div class="text-muted">'
            f"Assets: {assets_str} &middot; "
            f'<span class="{trend_cls}">{trend_arrow} {nar.trend}</span> &middot; '
            f"Conf: {nar.confidence:.0%} &middot; "
            f"Signals: {len(nar.signals)} &middot; "
            f"{updated}"
            f"</div>"
            f"</div>"
            f"</div></div>",
            unsafe_allow_html=True,
        )
