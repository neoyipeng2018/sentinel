"""Narrative evolution timeline view."""

from datetime import datetime

import plotly.graph_objects as go
import streamlit as st

from models.schemas import Narrative
from storage.narrative_store import get_narrative_history

RISK_LEVEL_NUM = {
    "critical": 4,
    "high": 3,
    "medium": 2,
    "low": 1,
}


def render_timeline(narratives: list[Narrative]) -> None:
    """Render the narrative evolution timeline."""
    st.header("Narrative Timeline")

    if not narratives:
        st.info("No active narratives to display.")
        return

    selected = st.selectbox(
        "Select narrative",
        options=narratives,
        format_func=lambda n: f"{n.title} ({n.risk_level.value})",
    )

    if selected:
        st.markdown(f"**{selected.title}**")
        st.markdown(f"*{selected.summary}*")
        st.markdown(f"Trend: **{selected.trend}** | Confidence: **{selected.confidence:.0%}**")

        # Show history if available
        history = get_narrative_history(selected.id)
        if history:
            timestamps = [datetime.fromisoformat(h["timestamp"]) for h in history]
            risk_values = [RISK_LEVEL_NUM.get(h["risk_level"], 1) for h in history]

            fig = go.Figure()
            fig.add_trace(
                go.Scatter(
                    x=timestamps,
                    y=risk_values,
                    mode="lines+markers",
                    name="Risk Level",
                    line=dict(color="#FF9100", width=2),
                    marker=dict(size=8),
                )
            )
            fig.update_layout(
                yaxis=dict(
                    tickvals=[1, 2, 3, 4],
                    ticktext=["Low", "Medium", "High", "Critical"],
                    range=[0.5, 4.5],
                ),
                xaxis_title="Time",
                yaxis_title="Risk Level",
                height=300,
                margin=dict(l=0, r=0, t=10, b=0),
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.caption("No history data yet. History builds as narratives are updated over time.")

        # Show associated signals
        st.subheader("Associated Signals")
        for sig in sorted(selected.signals, key=lambda s: s.timestamp, reverse=True):
            date_str = sig.timestamp.strftime('%b %d')
            st.markdown(
                f"- **{sig.title}** ({sig.source.value}, {date_str})"
            )
