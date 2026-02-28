"""Narrative evolution timeline view."""

from datetime import datetime

import plotly.graph_objects as go
import streamlit as st

from models.schemas import Narrative, RiskLevel, Signpost
from storage.narrative_store import get_narrative_history

RISK_LEVEL_NUM = {
    "critical": 4,
    "high": 3,
    "medium": 2,
    "low": 1,
}

RISK_COLORS = {
    RiskLevel.CRITICAL: "#FF1744",
    RiskLevel.HIGH: "#FF9100",
    RiskLevel.MEDIUM: "#FFEA00",
    RiskLevel.LOW: "#00E676",
}

# Distinct colors for narrative lines (up to 10 narratives)
LINE_PALETTE = [
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

TREND_DISPLAY = {
    "intensifying": ("&#9650;", "trend-up"),
    "stable": ("&#9654;", "trend-stable"),
    "fading": ("&#9660;", "trend-down"),
}


def _render_cascading_effects(effects: list) -> str:
    """Render cascading effects split into negative and positive sections."""
    from dashboard.overview import _render_cascading_effects as _render
    return _render(effects)


def _render_signposts(signposts: list[Signpost]) -> str:
    """Render risk signposts grouped by aggravating / mitigating."""
    from dashboard.overview import _render_signposts as _render
    return _render(signposts)


def _short_title(title: str, max_len: int = 40) -> str:
    """Truncate a narrative title for legend labels."""
    if len(title) <= max_len:
        return title
    return title[: max_len - 1].rsplit(" ", 1)[0] + "…"


def render_timeline(narratives: list[Narrative]) -> None:
    """Render the narrative trajectory chart — all narratives on one plot."""
    st.markdown(
        '<div class="section-header">'
        '<span class="pulse-dot"></span> NARRATIVE TRAJECTORIES'
        "</div>",
        unsafe_allow_html=True,
    )

    if not narratives:
        st.markdown(
            '<div class="cmd-panel" style="text-align: center; color: #4a5568;">'
            "No active narratives to display."
            "</div>",
            unsafe_allow_html=True,
        )
        return

    # -- Build the multi-line trajectory chart --
    fig = go.Figure()

    # Risk level zone bands
    zone_colors = [
        (0.5, 1.5, "rgba(0, 230, 118, 0.04)"),    # Low
        (1.5, 2.5, "rgba(255, 234, 0, 0.04)"),     # Medium
        (2.5, 3.5, "rgba(255, 145, 0, 0.04)"),     # High
        (3.5, 4.5, "rgba(255, 23, 68, 0.04)"),     # Critical
    ]
    for y0, y1, fill in zone_colors:
        fig.add_hrect(
            y0=y0, y1=y1,
            fillcolor=fill,
            line_width=0,
            layer="below",
        )

    has_any_history = False

    for i, narrative in enumerate(narratives):
        history = get_narrative_history(narrative.id)
        color = LINE_PALETTE[i % len(LINE_PALETTE)]
        label = _short_title(narrative.title)

        if history and len(history) > 1:
            has_any_history = True
            timestamps = [datetime.fromisoformat(h["timestamp"]) for h in history]
            risk_values = [RISK_LEVEL_NUM.get(h["risk_level"], 1) for h in history]

            fig.add_trace(
                go.Scatter(
                    x=timestamps,
                    y=risk_values,
                    mode="lines+markers",
                    name=label,
                    line=dict(color=color, width=2.5),
                    marker=dict(
                        size=7,
                        color=color,
                        line=dict(width=1.5, color="#0a0e14"),
                    ),
                    hovertemplate=(
                        f"<b>{narrative.title}</b><br>"
                        "Risk: %{customdata}<br>"
                        "%{x|%b %d %H:%M}<extra></extra>"
                    ),
                    customdata=[h["risk_level"].upper() for h in history],
                )
            )
        else:
            # Single data point — show as a dot at current position
            has_any_history = True
            risk_val = RISK_LEVEL_NUM.get(narrative.risk_level.value, 1)
            fig.add_trace(
                go.Scatter(
                    x=[narrative.last_updated],
                    y=[risk_val],
                    mode="markers",
                    name=label,
                    marker=dict(
                        size=10,
                        color=color,
                        line=dict(width=2, color="#0a0e14"),
                        symbol="diamond",
                    ),
                    hovertemplate=(
                        f"<b>{narrative.title}</b><br>"
                        f"Risk: {narrative.risk_level.value.upper()}<br>"
                        "%{x|%b %d %H:%M}<extra></extra>"
                    ),
                )
            )

    if not has_any_history:
        st.markdown(
            '<div class="cmd-panel" style="text-align: center; color: #4a5568;">'
            "No history data yet. Trajectories build as narratives are refreshed."
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
            tickfont=dict(family="SF Mono, Consolas, monospace",
                          size=10, color="#4a5568"),
        ),
        xaxis=dict(
            gridcolor="#1a2332",
            tickfont=dict(family="SF Mono, Consolas, monospace",
                          size=10, color="#4a5568"),
        ),
        height=350,
        margin=dict(l=0, r=0, t=10, b=0),
        showlegend=True,
        legend=dict(
            orientation="h",
            yanchor="top",
            y=-0.15,
            xanchor="left",
            x=0,
            font=dict(family="SF Mono, Consolas, monospace",
                      size=10, color="#8892a4"),
            bgcolor="rgba(0,0,0,0)",
        ),
        font=dict(family="SF Mono, Consolas, monospace", color="#8892a4"),
    )

    st.plotly_chart(fig, use_container_width=True)

    # -- Detail panel for selected narrative --
    st.markdown(
        '<div class="section-header" style="margin-top: 4px;">'
        "NARRATIVE DETAIL</div>",
        unsafe_allow_html=True,
    )

    selected = st.selectbox(
        "Select narrative",
        options=narratives,
        format_func=lambda n: f"{n.title} ({n.risk_level.value})",
        label_visibility="collapsed",
    )

    if selected:
        color = RISK_COLORS.get(selected.risk_level, "#4a5568")
        level = selected.risk_level.value
        trend_arrow, trend_cls = TREND_DISPLAY.get(
            selected.trend, ("&#9654;", "trend-stable")
        )

        st.markdown(
            f'<div class="cmd-panel cmd-panel-{level}">'
            f'<div style="display: flex; align-items: center; gap: 8px; '
            f'margin-bottom: 8px;">'
            f'<span class="badge badge-{level}">{level}</span>'
            f'<span style="font-weight: 600; color: #e0e4ec; font-size: 1rem;">'
            f"{selected.title}</span>"
            f"</div>"
            f'<div style="color: #8892a4; font-size: 0.82rem; margin-bottom: 6px;">'
            f"{selected.summary}</div>"
            f'<div class="text-muted">'
            f'<span class="{trend_cls}">{trend_arrow} {selected.trend}</span>'
            f" &middot; Confidence: {selected.confidence:.0%}"
            f" &middot; Signals: {len(selected.signals)}"
            f"</div>"
            + _render_cascading_effects(selected.cascading_effects)
            + _render_signposts(selected.signposts)
            + "</div>",
            unsafe_allow_html=True,
        )

        # Associated signals
        st.markdown(
            '<div class="section-header" style="margin-top: 12px;">'
            "ASSOCIATED SIGNALS</div>",
            unsafe_allow_html=True,
        )

        sorted_signals = sorted(
            selected.signals, key=lambda s: s.timestamp, reverse=True
        )

        if sorted_signals:
            rows = []
            for sig in sorted_signals:
                ts = sig.timestamp.strftime("%b %d")
                src = sig.source.value.upper()
                link_html = ""
                if sig.url:
                    link_html = (
                        f' <a href="{sig.url}" target="_blank" '
                        f'style="color: #00d4aa; font-size: 0.7rem; '
                        f'text-decoration: none;">[src]</a>'
                    )
                rows.append(
                    f'<div class="signal-row">'
                    f'<div class="signal-dot" '
                    f'style="background: {color};"></div>'
                    f"<div style=\"flex: 1;\">"
                    f'<span style="color: #e0e4ec; font-size: 0.82rem;">'
                    f"{sig.title}{link_html}</span>"
                    f'<div class="signal-meta">'
                    f'<span class="source-chip">{src}</span>'
                    f" &middot; {ts}"
                    f"</div></div></div>"
                )

            st.markdown(
                '<div class="cmd-panel" style="padding: 0; overflow: hidden;">'
                + "".join(rows)
                + "</div>",
                unsafe_allow_html=True,
            )
