"""Live alert feed showing recent signals."""

import streamlit as st

from models.schemas import Narrative, RiskLevel, Signal, SignalSource

SOURCE_ICONS = {
    SignalSource.NEWS: "📰",
    SignalSource.MARKET_DATA: "📊",
    SignalSource.SOCIAL: "💬",
}


def render_alerts(narratives: list[Narrative]) -> None:
    """Render the alert feed page."""
    st.header("Alert Feed")

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

    st.caption(f"Showing {len(filtered)} of {len(all_signals)} signals")

    for sig, nar in filtered[:50]:
        icon = SOURCE_ICONS.get(sig.source, "📌")
        risk_badge = nar.risk_level.value.upper()

        detail = (
            f"{sig.timestamp.strftime('%b %d, %H:%M')} · {sig.source.value}"
            f" · Narrative: {nar.title} · Risk: {risk_badge}"
        )
        st.markdown(
            f'**{icon} {sig.title}**\n<small style="color: #888;">{detail}</small>',
            unsafe_allow_html=True,
        )
        if sig.url:
            st.markdown(f"[Source link]({sig.url})")
        st.divider()
