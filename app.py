"""Sentinel - AI-powered financial risk narrative monitor."""

import streamlit as st

from ai.chains.narrative_extractor import extract_narratives
from ai.llm import get_llm
from config.overrides import get_custom_signals, has_custom_llm
from dashboard.alerts import render_alerts
from dashboard.briefing import render_briefing
from dashboard.overview import render_overview
from dashboard.timeline import render_timeline
from sources.market import detect_anomalies, fetch_market_data
from sources.news import fetch_news_signals
from sources.social import fetch_reddit_signals
from storage.narrative_store import (
    clear_narratives,
    init_db,
    load_active_narratives,
    save_narrative,
)

st.set_page_config(
    page_title="Sentinel",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Initialize database
init_db()


# --- Sidebar ---
with st.sidebar:
    st.title("🛡️ Sentinel")
    st.caption("AI Risk Narrative Monitor")

    page = st.radio(
        "Navigate",
        options=["Overview", "Alert Feed", "Timeline", "AI Briefing"],
        label_visibility="collapsed",
    )

    st.divider()

    # LLM provider selection
    if has_custom_llm():
        st.info("Using custom LLM from local_config.py")
    llm_provider = st.selectbox("LLM Provider", ["Cerebras (Free)", "OpenAI"])
    prefer_free = llm_provider == "Cerebras (Free)"

    st.divider()

    # Data refresh controls
    st.subheader("Data Sources")
    fetch_news = st.checkbox("News (RSS)", value=True)
    fetch_market = st.checkbox("Market Data", value=True)
    fetch_social = st.checkbox("Social (Reddit)", value=True)
    custom_signals_fn = get_custom_signals()
    fetch_custom = (
        st.checkbox("Custom Data", value=True) if custom_signals_fn else False
    )

    if st.button("🔄 Refresh Signals", type="primary", use_container_width=True):
        with st.spinner("Fetching signals..."):
            signals = []

            if fetch_news:
                st.text("Fetching news feeds...")
                signals.extend(fetch_news_signals())

            if fetch_market:
                st.text("Fetching market data...")
                data = fetch_market_data()
                signals.extend(detect_anomalies(data))

            if fetch_social:
                st.text("Fetching social signals...")
                signals.extend(fetch_reddit_signals())

            if fetch_custom and custom_signals_fn:
                st.text("Fetching custom signals...")
                signals.extend(custom_signals_fn())

            st.text(f"Collected {len(signals)} signals")

            if signals:
                st.text("Extracting narratives...")
                llm = get_llm(prefer_free=prefer_free)
                narratives = extract_narratives(signals, llm)

                clear_narratives()
                for nar in narratives:
                    save_narrative(nar)

                st.success(f"Extracted {len(narratives)} risk narratives")

    st.divider()
    narratives = load_active_narratives()
    st.caption(f"{len(narratives)} active narratives")


# --- Main Content ---
if page == "Overview":
    render_overview(narratives)
elif page == "Alert Feed":
    render_alerts(narratives)
elif page == "Timeline":
    render_timeline(narratives)
elif page == "AI Briefing":
    llm = get_llm(prefer_free=prefer_free)
    render_briefing(narratives, llm)
