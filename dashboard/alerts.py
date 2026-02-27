"""Live alert feed showing recent signals."""

import streamlit as st

from models.schemas import Narrative, RiskLevel, Signal, SignalSource

RISK_DOT_COLORS = {
    RiskLevel.CRITICAL: "#FF1744",
    RiskLevel.HIGH: "#FF9100",
    RiskLevel.MEDIUM: "#FFEA00",
    RiskLevel.LOW: "#00E676",
}

SOURCE_LABELS = {
    SignalSource.NEWS: "NEWS",
    SignalSource.MARKET_DATA: "MARKET",
    SignalSource.SOCIAL: "SOCIAL",
    SignalSource.CUSTOM: "CUSTOM",
}


def render_alerts(narratives: list[Narrative]) -> None:
    """Render the alert feed page."""
    st.markdown(
        '<div class="section-header">'
        '<span class="pulse-dot"></span> LIVE SIGNALS'
        "</div>",
        unsafe_allow_html=True,
    )

    # Collect all signals from active narratives
    all_signals: list[tuple[Signal, Narrative]] = []
    for nar in narratives:
        for sig in nar.signals:
            all_signals.append((sig, nar))

    # Sort by timestamp descending
    all_signals.sort(key=lambda x: x[0].timestamp, reverse=True)

    # Filters
    col1, col2 = st.columns(2)
    with col1:
        source_filter = st.multiselect(
            "Source",
            options=[s.value for s in SignalSource],
            default=[s.value for s in SignalSource],
        )
    with col2:
        risk_filter = st.multiselect(
            "Risk Level",
            options=[r.value for r in RiskLevel],
            default=[r.value for r in RiskLevel],
        )

    # Apply filters
    filtered = [
        (sig, nar)
        for sig, nar in all_signals
        if sig.source.value in source_filter and nar.risk_level.value in risk_filter
    ]

    st.markdown(
        f'<div class="text-muted" style="margin-bottom: 8px;">'
        f"SHOWING {len(filtered)} OF {len(all_signals)} SIGNALS</div>",
        unsafe_allow_html=True,
    )

    # Render signal feed
    feed_html_parts = ['<div class="cmd-panel" style="padding: 0; overflow: hidden;">']

    for sig, nar in filtered[:50]:
        dot_color = RISK_DOT_COLORS.get(nar.risk_level, "#4a5568")
        source_label = SOURCE_LABELS.get(sig.source, sig.source.value.upper())
        risk_level = nar.risk_level.value
        ts = sig.timestamp.strftime("%b %d, %H:%M")

        link_html = ""
        if sig.url:
            link_html = (
                f' <a href="{sig.url}" target="_blank" '
                f'style="color: #00d4aa; font-size: 0.7rem; text-decoration: none;">'
                f"[src]</a>"
            )

        feed_html_parts.append(
            f'<div class="signal-row">'
            f'<div class="signal-dot" style="background: {dot_color};"></div>'
            f"<div style=\"flex: 1;\">"
            f'<div style="color: #e0e4ec; font-size: 0.82rem; font-weight: 500;">'
            f"{sig.title}{link_html}</div>"
            f'<div class="signal-meta">'
            f'<span class="source-chip">{source_label}</span> '
            f'<span style="margin: 0 4px;">&middot;</span> '
            f'<span class="badge badge-{risk_level}" '
            f'style="font-size: 0.55rem; padding: 1px 5px;">{risk_level}</span> '
            f'<span style="margin: 0 4px;">&middot;</span> '
            f"{nar.title} "
            f'<span style="margin: 0 4px;">&middot;</span> '
            f"{ts}"
            f"</div>"
            f"</div>"
            f"</div>"
        )

    feed_html_parts.append("</div>")

    if filtered:
        st.markdown("".join(feed_html_parts), unsafe_allow_html=True)
    else:
        st.markdown(
            '<div class="cmd-panel" style="text-align: center; color: #4a5568;">'
            "No signals match the current filters."
            "</div>",
            unsafe_allow_html=True,
        )
