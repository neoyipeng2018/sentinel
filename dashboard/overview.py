"""Risk overview dashboard page."""

import math
from datetime import datetime

import plotly.graph_objects as go
import streamlit as st

from ai.chains.risk_assessor import compute_asset_risk_scores, get_top_risks
from ai.chains.trend_analyzer import classify_emerging_risk
from models.schemas import AssetClass, CounterNarrative, Narrative, RiskLevel, Signpost
from storage.narrative_store import get_risk_score_history

RISK_COLORS = {
    RiskLevel.CRITICAL: "#FF1744",
    RiskLevel.HIGH: "#FF9100",
    RiskLevel.MEDIUM: "#FFEA00",
    RiskLevel.LOW: "#00E676",
}

ASSET_LABELS = {
    AssetClass.EQUITIES: "Equities",
    AssetClass.CREDIT: "Credit",
    AssetClass.RATES: "Rates",
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


def _render_cascading_effects(effects: list) -> str:
    """Render the causal chain of second/third order effects."""
    if not effects:
        return ""

    sorted_effects = sorted(effects, key=lambda e: e.order)
    rows = ""
    for eff in sorted_effects:
        order_label = f"{eff.order}nd" if eff.order == 2 else f"{eff.order}rd"
        assets_html = ""
        if eff.affected_sub_assets:
            chips = " ".join(
                f'<span class="cascade-asset">{a}</span>'
                for a in eff.affected_sub_assets
            )
            assets_html = f'<div class="cascade-assets">{chips}</div>'
        rows += (
            f'<div class="cascade-row">'
            f'<span class="cascade-order">{order_label}</span>'
            f'<div class="cascade-connector"></div>'
            f"<div>"
            f'<div class="cascade-effect">{eff.effect}</div>'
            f'<div class="cascade-mechanism">{eff.mechanism}</div>'
            f"{assets_html}"
            f"</div>"
            f"</div>"
        )

    return (
        f'<div class="cascade-chain">'
        f'<div class="cascade-header">CASCADING EFFECTS</div>'
        f"{rows}"
        f"</div>"
    )


def _render_signposts(signposts: list[Signpost]) -> str:
    """Render risk signposts grouped by aggravating / mitigating."""
    if not signposts:
        return ""

    aggravating = [s for s in signposts if s.type == "aggravating"]
    mitigating = [s for s in signposts if s.type == "mitigating"]

    rows = ""
    for sp in aggravating:
        rows += (
            f'<div class="cascade-row">'
            f'<span class="cascade-order" style="background: rgba(255,23,68,0.15); '
            f'color: #ff5252;">&#9650;</span>'
            f'<div class="cascade-connector" style="border-color: #ff5252;"></div>'
            f"<div>"
            f'<div class="cascade-effect" style="color: #ff8a80;">{sp.factor}</div>'
            f'<div class="cascade-mechanism">{sp.detail}</div>'
            f"</div></div>"
        )
    for sp in mitigating:
        rows += (
            f'<div class="cascade-row">'
            f'<span class="cascade-order" style="background: rgba(0,230,118,0.15); '
            f'color: #69f0ae;">&#9660;</span>'
            f'<div class="cascade-connector" style="border-color: #69f0ae;"></div>'
            f"<div>"
            f'<div class="cascade-effect" style="color: #b9f6ca;">{sp.factor}</div>'
            f'<div class="cascade-mechanism">{sp.detail}</div>'
            f"</div></div>"
        )

    return (
        f'<div class="cascade-chain" style="border-left-color: #546e7a;">'
        f'<div class="cascade-header" style="color: #78909c;">SIGNPOSTS</div>'
        f"{rows}"
        f"</div>"
    )


def _render_counter_narrative(counter: CounterNarrative) -> str:
    """Render a counter-narrative (blindspot) section."""
    conf_pct = f"{counter.confidence:.0%}"
    return (
        '<div class="cascade-chain" style="border-left-color: #4a6fa5;">'
        '<div class="cascade-header" style="color: #4a6fa5;">'
        "COUNTER-NARRATIVE</div>"
        f'<div style="color: #b0bec5; font-size: 0.8rem; line-height: 1.5; '
        f'margin-bottom: 4px;">{counter.counter_argument}</div>'
        f'<div style="color: #607d8b; font-size: 0.75rem; line-height: 1.4; '
        f'margin-bottom: 4px;"><strong>Basis:</strong> {counter.basis}</div>'
        f'<div style="color: #546e7a; font-size: 0.7rem;">'
        f"Confidence: {conf_pct}</div>"
        "</div>"
    )


LOOKBACK_OPTIONS = {
    "24h": 24,
    "3d": 72,
    "7d": 168,
    "30d": 720,
}


def _render_risk_time_series(selected_assets: list[AssetClass] | None = None) -> None:
    """Render a multi-line Plotly chart of risk scores over time."""
    st.markdown(
        '<div class="section-header" style="margin-top: 16px;">'
        "RISK TIME SERIES</div>",
        unsafe_allow_html=True,
    )

    lookback_label = st.selectbox(
        "Lookback period",
        options=list(LOOKBACK_OPTIONS.keys()),
        index=0,  # default 24h
        label_visibility="collapsed",
    )
    lookback_hours = LOOKBACK_OPTIONS[lookback_label]

    history = get_risk_score_history(lookback_hours=lookback_hours)

    if not history:
        st.markdown(
            '<div class="cmd-panel" style="text-align: center; color: #4a5568;">'
            "No time series data yet. Data accumulates with each refresh."
            "</div>",
            unsafe_allow_html=True,
        )
        return

    # Group by asset class
    asset_filter = set(selected_assets) if selected_assets else {ac for ac in AssetClass}
    series: dict[str, dict] = {}
    for row in history:
        ac_value = row["asset_class"]
        try:
            ac = AssetClass(ac_value)
        except ValueError:
            continue
        if ac not in asset_filter:
            continue
        if ac_value not in series:
            series[ac_value] = {"timestamps": [], "scores": [], "counts": [], "titles": []}
        series[ac_value]["timestamps"].append(datetime.fromisoformat(row["timestamp"]))
        series[ac_value]["scores"].append(row["score"])
        series[ac_value]["counts"].append(row["narrative_count"])
        series[ac_value]["titles"].append(row["top_narrative_title"] or "—")

    if not series:
        st.markdown(
            '<div class="cmd-panel" style="text-align: center; color: #4a5568;">'
            "No data for selected asset classes in this period."
            "</div>",
            unsafe_allow_html=True,
        )
        return

    line_colors = {
        "equities": "#00d4aa",
        "credit": "#4fc3f7",
        "rates": "#81d4fa",
        "private_markets": "#ba68c8",
        "real_estate": "#ff8a65",
        "commodities": "#ffd54f",
        "fx": "#e0e4ec",
    }

    fig = go.Figure()

    # Risk zone bands
    zone_bands = [
        (0, 2.5, "rgba(0, 230, 118, 0.04)", "Low"),
        (2.5, 5, "rgba(255, 234, 0, 0.04)", "Medium"),
        (5, 7.5, "rgba(255, 145, 0, 0.04)", "High"),
        (7.5, 10, "rgba(255, 23, 68, 0.04)", "Critical"),
    ]
    for y0, y1, fill, _ in zone_bands:
        fig.add_hrect(y0=y0, y1=y1, fillcolor=fill, line_width=0, layer="below")

    for ac_value, data in series.items():
        label = ASSET_LABELS.get(AssetClass(ac_value), ac_value)
        color = line_colors.get(ac_value, "#8892a4")
        hover_text = [
            f"<b>{label}</b><br>"
            f"Score: {s:.1f}<br>"
            f"Narratives: {c}<br>"
            f"Top: {t}"
            for s, c, t in zip(data["scores"], data["counts"], data["titles"])
        ]
        fig.add_trace(
            go.Scatter(
                x=data["timestamps"],
                y=data["scores"],
                mode="lines+markers",
                name=label,
                line=dict(color=color, width=2),
                marker=dict(size=6, color=color),
                hovertext=hover_text,
                hoverinfo="text",
            )
        )

    fig.update_layout(
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        yaxis=dict(
            range=[0, 10.5],
            tickvals=[0, 2.5, 5, 7.5, 10],
            ticktext=["0", "LOW", "MED", "HIGH", "CRIT"],
            gridcolor="#1a2332",
            tickfont=dict(family="SF Mono, Consolas, monospace", size=10, color="#4a5568"),
        ),
        xaxis=dict(
            gridcolor="#1a2332",
            tickfont=dict(family="SF Mono, Consolas, monospace", size=10, color="#4a5568"),
        ),
        height=320,
        margin=dict(l=0, r=0, t=10, b=0),
        legend=dict(
            font=dict(family="SF Mono, Consolas, monospace", size=10, color="#8892a4"),
            bgcolor="rgba(0,0,0,0)",
        ),
        font=dict(family="SF Mono, Consolas, monospace", color="#8892a4"),
    )

    st.plotly_chart(fig, use_container_width=True)


def _render_emerging_risks(narratives: list[Narrative]) -> None:
    """Render emerging risk callout cards for newly-appeared escalating risks."""
    emerging = [n for n in narratives if classify_emerging_risk(n)]

    if not emerging:
        return

    st.markdown(
        '<div class="section-header" style="margin-top: 16px;">'
        "EMERGING RISKS</div>",
        unsafe_allow_html=True,
    )

    for nar in emerging:
        color = RISK_COLORS.get(nar.risk_level, "#FF9100")
        level = nar.risk_level.value
        age_delta = datetime.utcnow() - nar.first_seen
        if age_delta.days > 0:
            age_str = f"{age_delta.days}d ago"
        else:
            hours = age_delta.seconds // 3600
            age_str = f"{hours}h ago" if hours > 0 else "just now"

        # Build sub-asset detail string
        asset_parts = []
        for a in nar.affected_assets:
            label = ASSET_LABELS.get(a, a.value)
            subs = nar.asset_detail.get(a)
            if subs:
                label += f" ({', '.join(subs)})"
            asset_parts.append(label)
        assets_str = ", ".join(asset_parts) if asset_parts else "—"

        st.markdown(
            f'<div class="cmd-panel" style="border-left: 3px dashed {color}; '
            f'background: rgba(255,255,255,0.02);">'
            f'<div style="display: flex; align-items: center; gap: 8px; '
            f'margin-bottom: 6px;">'
            f'<span class="badge badge-{level}" '
            f'style="font-size: 0.6rem; letter-spacing: 0.1em;">EMERGING</span>'
            f'<span class="badge badge-{level}">{level}</span>'
            f'<span style="font-weight: 600; color: #e0e4ec; font-size: 0.9rem;">'
            f"{nar.title}</span>"
            f"</div>"
            f'<div style="color: #8892a4; font-size: 0.8rem; line-height: 1.5; '
            f'margin-bottom: 6px;">{nar.summary}</div>'
            f'<div class="text-muted">'
            f"Assets: {assets_str} &middot; "
            f"First seen: {age_str} &middot; "
            f"Signals: {len(nar.signals)} &middot; "
            f"Trend: {nar.trend}"
            f"</div>"
            + (
                _render_cascading_effects(nar.cascading_effects)
                if nar.cascading_effects
                else ""
            )
            + (
                _render_counter_narrative(nar.counter_narrative)
                if nar.counter_narrative
                else ""
            )
            + _render_signposts(nar.signposts)
            + "</div>",
            unsafe_allow_html=True,
        )


def render_overview(
    narratives: list[Narrative],
    selected_assets: list[AssetClass] | None = None,
) -> None:
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
    all_scores = compute_asset_risk_scores(narratives)
    # Filter heatmap to selected asset classes
    if selected_assets:
        scores = {ac: all_scores[ac] for ac in selected_assets if ac in all_scores}
    else:
        scores = all_scores

    st.markdown(
        '<div class="section-header">RISK HEATMAP BY ASSET CLASS</div>',
        unsafe_allow_html=True,
    )
    if scores:
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

    # Risk time series chart
    _render_risk_time_series(selected_assets)

    # Emerging risk highlights
    _render_emerging_risks(narratives)

    # Top narratives
    st.markdown(
        '<div class="section-header" style="margin-top: 16px;">'
        "TOP RISK NARRATIVES</div>",
        unsafe_allow_html=True,
    )

    asset_filter = set(selected_assets) if selected_assets else None
    top = get_top_risks(narratives, n=10)
    for nar in top:
        color = RISK_COLORS[nar.risk_level]
        level = nar.risk_level.value
        asset_parts = []
        for a in nar.affected_assets:
            if asset_filter and a not in asset_filter:
                continue
            label = ASSET_LABELS.get(a, a.value)
            subs = nar.asset_detail.get(a)
            if subs:
                label += f" ({', '.join(subs)})"
            asset_parts.append(label)
        assets_str = ", ".join(asset_parts) if asset_parts else "—"

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
            + (
                _render_cascading_effects(nar.cascading_effects)
                if nar.cascading_effects
                else ""
            )
            + (
                _render_counter_narrative(nar.counter_narrative)
                if nar.counter_narrative
                else ""
            )
            + _render_signposts(nar.signposts)
            + "</div>"
            "</div></div>",
            unsafe_allow_html=True,
        )
