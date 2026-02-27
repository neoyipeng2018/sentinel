"""AI risk briefing page."""

from datetime import datetime

import streamlit as st
from langchain_core.language_models import BaseChatModel

from ai.chains.briefing_generator import generate_briefing
from models.schemas import Narrative


def render_briefing(narratives: list[Narrative], llm: BaseChatModel) -> None:
    """Render the AI risk briefing page."""
    st.markdown(
        '<div class="section-header">'
        '<span class="pulse-dot"></span> AI RISK BRIEFING'
        "</div>",
        unsafe_allow_html=True,
    )

    if not narratives:
        st.markdown(
            '<div class="cmd-panel" style="text-align: center; color: #4a5568;">'
            "No active narratives to generate a briefing from."
            "</div>",
            unsafe_allow_html=True,
        )
        return

    if st.button("GENERATE BRIEFING", type="primary"):
        with st.spinner("Generating risk briefing..."):
            briefing = generate_briefing(narratives, llm)

        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S UTC")

        st.markdown(
            '<div class="briefing-panel">'
            f'<div class="briefing-header">RISK BRIEFING &middot; {now_str}</div>'
            f'<div class="briefing-text">{briefing.summary}</div>'
            "</div>",
            unsafe_allow_html=True,
        )

        # Key risks
        st.markdown(
            '<div class="section-header" style="margin-top: 16px;">'
            "KEY RISKS</div>",
            unsafe_allow_html=True,
        )

        risks_html = ['<div class="briefing-panel" style="padding: 12px 20px;">']
        for i, risk in enumerate(briefing.key_risks, 1):
            risks_html.append(
                f'<div style="display: flex; align-items: flex-start; gap: 10px; '
                f'padding: 8px 0; border-bottom: 1px solid #111827;">'
                f'<div style="color: #FF9100; font-weight: 700; font-size: 0.85rem; '
                f'min-width: 20px;">{i:02d}</div>'
                f'<div style="color: #c5c8d4; font-size: 0.85rem; '
                f'line-height: 1.5;">{risk}</div>'
                f"</div>"
            )
        risks_html.append("</div>")

        st.markdown("".join(risks_html), unsafe_allow_html=True)

    else:
        st.markdown(
            '<div class="cmd-panel" style="text-align: center; padding: 32px;">'
            '<div style="color: #4a5568; font-size: 0.85rem; margin-bottom: 12px;">'
            "Click GENERATE BRIEFING to create an AI-powered risk assessment."
            "</div>"
            '<div style="color: #2a3442; font-size: 2rem;">&#9888;</div>'
            "</div>",
            unsafe_allow_html=True,
        )
