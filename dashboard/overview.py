"""Risk overview dashboard page."""

import math
from datetime import datetime

import plotly.graph_objects as go
import streamlit as st

from ai.chains.risk_assessor import compute_asset_risk_scores, get_top_risks
from ai.chains.trend_analyzer import classify_emerging_risk
from models.schemas import (
    AssetClass,
    AssetImpact,
    CounterNarrative,
    Narrative,
    RiskLevel,
    Signal,
    Signpost,
)

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


def _render_effect_rows(effects: list, color: str, icon: str) -> str:
    """Render rows for a list of cascading effects with a given color theme."""
    rows = ""
    for eff in sorted(effects, key=lambda e: e.order):
        order_label = (
            f"{eff.order}nd" if eff.order == 2 else f"{eff.order}rd"
        )
        assets_html = ""
        at_risk = getattr(eff, "sub_assets_at_risk", [])
        to_benefit = getattr(eff, "sub_assets_to_benefit", [])
        if at_risk:
            chips = " ".join(
                f'<span class="cascade-asset" '
                f'style="border-color: #ff5252; color: #ff8a80;">'
                f"{a}</span>"
                for a in at_risk
            )
            assets_html += (
                f'<div class="cascade-assets">'
                f'<span style="color: #ff5252; font-size: 0.6rem; '
                f'font-weight: 700;">&#9660;</span> {chips}</div>'
            )
        if to_benefit:
            chips = " ".join(
                f'<span class="cascade-asset" '
                f'style="border-color: #69f0ae; color: #b9f6ca;">'
                f"{a}</span>"
                for a in to_benefit
            )
            assets_html += (
                f'<div class="cascade-assets">'
                f'<span style="color: #69f0ae; font-size: 0.6rem; '
                f'font-weight: 700;">&#9650;</span> {chips}</div>'
            )
        timeframe = getattr(eff, "timeframe", "")
        tf_html = (
            f' <span style="color: #78909c; font-size: 0.65rem; '
            f'font-weight: 600; border: 1px solid #37474f; '
            f'border-radius: 3px; padding: 0 4px; '
            f'margin-left: 4px;">{timeframe}</span>'
            if timeframe
            else ""
        )
        rows += (
            f'<div class="cascade-row">'
            f'<span class="cascade-order" style="background: {color}15; '
            f'color: {color};">{icon} {order_label}</span>'
            f'<div class="cascade-connector" '
            f'style="border-color: {color};"></div>'
            f"<div>"
            f'<div class="cascade-effect">{eff.effect}{tf_html}</div>'
            f'<div class="cascade-mechanism">{eff.mechanism}</div>'
            f"{assets_html}"
            f"</div>"
            f"</div>"
        )
    return rows


def _render_cascading_effects(effects: list) -> str:
    """Render cascading effects split into negative and positive sections."""
    if not effects:
        return ""

    negative = [e for e in effects if getattr(e, "direction", "negative") != "positive"]
    positive = [e for e in effects if getattr(e, "direction", None) == "positive"]

    html = ""
    if negative:
        rows = _render_effect_rows(negative, "#ff5252", "&#9660;")
        html += (
            f'<div class="cascade-chain" style="border-left-color: #ff5252;">'
            f'<div class="cascade-header" style="color: #ff8a80;">'
            f"CASCADING EFFECTS &mdash; NEGATIVE</div>"
            f"{rows}</div>"
        )
    if positive:
        rows = _render_effect_rows(positive, "#69f0ae", "&#9650;")
        html += (
            f'<div class="cascade-chain" style="border-left-color: #69f0ae;">'
            f'<div class="cascade-header" style="color: #b9f6ca;">'
            f"CASCADING EFFECTS &mdash; POSITIVE</div>"
            f"{rows}</div>"
        )
    return html


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
    """Render a collapsible counter-narrative (blindspot) section."""
    conf_pct = f"{counter.confidence:.0%}"
    return (
        f'<details style="margin-top: 6px;">'
        f'<summary style="color: #4a6fa5; font-size: 0.7rem; font-weight: 700; '
        f'letter-spacing: 0.1em; cursor: pointer; list-style: none; '
        f'user-select: none;">'
        f"&#9656; COUNTER-NARRATIVE</summary>"
        f'<div class="cascade-chain" style="border-left-color: #4a6fa5; '
        f'margin-top: 4px;">'
        f'<div style="color: #b0bec5; font-size: 0.8rem; line-height: 1.5; '
        f'margin-bottom: 4px;">{counter.counter_argument}</div>'
        f'<div style="color: #607d8b; font-size: 0.75rem; line-height: 1.4; '
        f'margin-bottom: 4px;"><strong>Basis:</strong> {counter.basis}</div>'
        f'<div style="color: #546e7a; font-size: 0.7rem;">'
        f"Confidence: {conf_pct}</div>"
        f"</div></details>"
    )


SOURCE_LABELS = {
    "news": "NEWS",
    "market_data": "MARKET",
    "social": "SOCIAL",
    "custom": "CUSTOM",
}


def _render_sources(signals: list[Signal]) -> str:
    """Render a collapsible SOURCES block listing signal titles with links."""
    if not signals:
        return ""

    rows = ""
    for sig in signals:
        src_label = SOURCE_LABELS.get(sig.source.value, sig.source.value.upper())
        ts = sig.timestamp.strftime("%b %d, %H:%M")
        if sig.url:
            title_html = (
                f'<a href="{sig.url}" target="_blank" '
                f'style="color: #e0e4ec; text-decoration: none;">{sig.title}</a>'
                f' <a href="{sig.url}" target="_blank" '
                f'style="color: #00d4aa; font-size: 0.7rem; text-decoration: none;">'
                f"[src]</a>"
            )
        else:
            title_html = f'<span style="color: #e0e4ec;">{sig.title}</span>'
        rows += (
            f'<div class="cascade-row">'
            f'<span class="cascade-order" style="background: rgba(0,212,170,0.10); '
            f'color: #00d4aa; font-size: 0.6rem;">{src_label}</span>'
            f'<div class="cascade-connector" style="border-color: #2a3a4a;"></div>'
            f"<div>"
            f'<div class="cascade-effect" style="font-size: 0.8rem;">{title_html}</div>'
            f'<div class="cascade-mechanism">{ts}</div>'
            f"</div>"
            f"</div>"
        )

    return (
        f'<details style="margin-top: 6px;">'
        f'<summary style="color: #546e7a; font-size: 0.7rem; font-weight: 700; '
        f'letter-spacing: 0.1em; cursor: pointer; list-style: none; '
        f'user-select: none;">'
        f"&#9656; SOURCES ({len(signals)})</summary>"
        f'<div class="cascade-chain" style="border-left-color: #2a3a4a; '
        f'margin-top: 4px;">'
        f"{rows}"
        f"</div>"
        f"</details>"
    )


def _render_asset_impacts(
    at_risk: dict[AssetClass, list[AssetImpact]],
    to_benefit: dict[AssetClass, list[AssetImpact]],
) -> str:
    """Render assets split into 'at risk' and 'to benefit' sections."""
    html = ""
    if at_risk:
        chips = ""
        for ac, imps in at_risk.items():
            label = ASSET_LABELS.get(ac, ac.value)
            for imp in imps:
                title_attr = f' title="{imp.explanation}"' if imp.explanation else ""
                chips += (
                    f'<span class="cascade-asset" style="border-color: #ff5252;'
                    f' color: #ff8a80;"{title_attr}>{label}: {imp.asset}</span> '
                )
        html += (
            f'<div style="margin-top: 4px;">'
            f'<span style="color: #ff5252; font-size: 0.7rem; font-weight: 700; '
            f'letter-spacing: 0.05em;">&#9660; AT RISK</span> {chips}</div>'
        )
    if to_benefit:
        chips = ""
        for ac, imps in to_benefit.items():
            label = ASSET_LABELS.get(ac, ac.value)
            for imp in imps:
                title_attr = f' title="{imp.explanation}"' if imp.explanation else ""
                chips += (
                    f'<span class="cascade-asset" style="border-color: #69f0ae;'
                    f' color: #b9f6ca;"{title_attr}>{label}: {imp.asset}</span> '
                )
        html += (
            f'<div style="margin-top: 4px;">'
            f'<span style="color: #69f0ae; font-size: 0.7rem; font-weight: 700; '
            f'letter-spacing: 0.05em;">&#9650; BENEFIT</span> {chips}</div>'
        )
    return html


RISK_LEVEL_NUM = {
    "critical": 4,
    "high": 3,
    "medium": 2,
    "low": 1,
}

# Distinct colors for narrative lines
_LINE_PALETTE = [
    "#00d4aa",  # teal
    "#FF9100",  # orange
    "#7C4DFF",  # purple
    "#FF1744",  # red
    "#00B0FF",  # blue
    "#FFEA00",  # yellow
    "#E040FB",  # pink
    "#76FF03",  # lime
    "#FF6D00",  # deep orange
    "#18FFFF",  # cyan
]


def _short_title(title: str, max_len: int = 40) -> str:
    if len(title) <= max_len:
        return title
    return title[: max_len - 1].rsplit(" ", 1)[0] + "…"


def _render_narrative_trajectories(
    narratives: list[Narrative],
    selected_assets: list[AssetClass] | None = None,
) -> None:
    """Render a multi-line chart of narrative risk-level trajectories."""
    from storage.narrative_store import get_narrative_history

    st.markdown(
        '<div class="section-header" style="margin-top: 16px;">'
        "NARRATIVE TRAJECTORIES</div>",
        unsafe_allow_html=True,
    )

    # Filter narratives by selected asset classes
    if selected_assets:
        asset_filter = set(selected_assets)
        filtered = [
            n for n in narratives
            if asset_filter & set(n.affected_assets)
        ]
    else:
        filtered = list(narratives)

    if not filtered:
        st.markdown(
            '<div class="cmd-panel" style="text-align: center; color: #4a5568;">'
            "No narratives for selected asset classes."
            "</div>",
            unsafe_allow_html=True,
        )
        return

    fig = go.Figure()

    # Risk level zone bands
    zone_colors = [
        (0.5, 1.5, "rgba(0, 230, 118, 0.04)"),
        (1.5, 2.5, "rgba(255, 234, 0, 0.04)"),
        (2.5, 3.5, "rgba(255, 145, 0, 0.04)"),
        (3.5, 4.5, "rgba(255, 23, 68, 0.04)"),
    ]
    for y0, y1, fill in zone_colors:
        fig.add_hrect(y0=y0, y1=y1, fillcolor=fill, line_width=0, layer="below")

    has_data = False

    for i, narrative in enumerate(filtered):
        history = get_narrative_history(narrative.id)
        color = _LINE_PALETTE[i % len(_LINE_PALETTE)]
        label = _short_title(narrative.title)

        if history and len(history) > 1:
            has_data = True
            timestamps = [datetime.fromisoformat(h["timestamp"]) for h in history]
            risk_values = [RISK_LEVEL_NUM.get(h["risk_level"], 1) for h in history]
            signal_counts = [h.get("signal_count", 1) or 1 for h in history]
            max_sc = max(signal_counts)
            marker_sizes = [
                max(6, min(22, 6 + 16 * (sc / max_sc))) for sc in signal_counts
            ]

            fig.add_trace(
                go.Scatter(
                    x=timestamps,
                    y=risk_values,
                    mode="lines+markers",
                    name=label,
                    line=dict(color=color, width=2.5),
                    marker=dict(
                        size=marker_sizes,
                        color=color,
                        line=dict(width=1.5, color="#0a0e14"),
                    ),
                    hovertemplate=(
                        f"<b>{narrative.title}</b><br>"
                        "Risk: %{customdata[0]}<br>"
                        "Signals: %{customdata[1]}<br>"
                        "%{x|%b %d %H:%M}<extra></extra>"
                    ),
                    customdata=[
                        [h["risk_level"].upper(), h.get("signal_count", 0)]
                        for h in history
                    ],
                )
            )
        else:
            has_data = True
            risk_val = RISK_LEVEL_NUM.get(narrative.risk_level.value, 1)
            sc = len(narrative.signals)
            fig.add_trace(
                go.Scatter(
                    x=[narrative.last_updated],
                    y=[risk_val],
                    mode="markers",
                    name=label,
                    marker=dict(
                        size=max(8, min(22, 8 + sc)),
                        color=color,
                        line=dict(width=2, color="#0a0e14"),
                        symbol="diamond",
                    ),
                    hovertemplate=(
                        f"<b>{narrative.title}</b><br>"
                        f"Risk: {narrative.risk_level.value.upper()}<br>"
                        f"Signals: {sc}<br>"
                        "%{x|%b %d %H:%M}<extra></extra>"
                    ),
                )
            )

    if not has_data:
        st.markdown(
            '<div class="cmd-panel" style="text-align: center; color: #4a5568;">'
            "No trajectory data yet. Data builds with each refresh."
            "</div>",
            unsafe_allow_html=True,
        )
        return

    fig.update_layout(
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        yaxis=dict(
            tickvals=[1, 2, 3, 4],
            ticktext=["LOW", "MEDIUM", "HIGH", "CRITICAL"],
            range=[0.5, 4.5],
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
            orientation="h",
            yanchor="top",
            y=-0.15,
            xanchor="left",
            x=0,
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
            + _render_asset_impacts(nar.assets_at_risk, nar.assets_to_benefit)
            + f'<div class="text-muted">'
            f"First seen: {age_str} &middot; "
            f"Signals: {len(nar.signals)} &middot; "
            f"Trend: {nar.trend}"
            f"</div>"
            + (
                _render_cascading_effects(nar.cascading_effects)
                if nar.cascading_effects
                else ""
            )
            + _render_signposts(nar.signposts)
            + (
                _render_counter_narrative(nar.counter_narrative)
                if nar.counter_narrative
                else ""
            )
            + _render_sources(nar.signals)
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

    # Narrative trajectory chart
    _render_narrative_trajectories(narratives, selected_assets)

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

        # Filter asset impacts to selected asset classes
        if asset_filter:
            filtered_risk = {
                a: imps for a, imps in nar.assets_at_risk.items()
                if a in asset_filter
            }
            filtered_benefit = {
                a: imps for a, imps in nar.assets_to_benefit.items()
                if a in asset_filter
            }
        else:
            filtered_risk = nar.assets_at_risk
            filtered_benefit = nar.assets_to_benefit

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
            + _render_asset_impacts(filtered_risk, filtered_benefit)
            + f'<div class="text-muted">'
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
            + _render_signposts(nar.signposts)
            + (
                _render_counter_narrative(nar.counter_narrative)
                if nar.counter_narrative
                else ""
            )
            + _render_sources(nar.signals)
            + "</div>"
            "</div></div>",
            unsafe_allow_html=True,
        )
