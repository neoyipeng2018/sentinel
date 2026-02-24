"""AI risk briefing page."""

import streamlit as st
from langchain_core.language_models import BaseChatModel

from ai.chains.briefing_generator import generate_briefing
from models.schemas import Narrative


def render_briefing(narratives: list[Narrative], llm: BaseChatModel) -> None:
    """Render the AI risk briefing page."""
    st.header("AI Risk Briefing")

    if not narratives:
        st.info("No active narratives to generate a briefing from.")
        return

    if st.button("Generate Briefing", type="primary"):
        with st.spinner("Generating risk briefing..."):
            briefing = generate_briefing(narratives, llm)

        st.markdown(briefing.summary)

        st.divider()
        st.subheader("Key Risks")
        for i, risk in enumerate(briefing.key_risks, 1):
            st.markdown(f"{i}. {risk}")

    else:
        st.markdown("Click **Generate Briefing** to create an AI-powered risk assessment.")
