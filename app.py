"""Sentinel - AI-powered financial risk narrative monitor."""

from datetime import datetime

import streamlit as st

from ai.chains.narrative_extractor import extract_narratives
from ai.chains.trend_analyzer import compute_quantitative_trend
from ai.llm import get_llm
from config.overrides import get_custom_signals, has_custom_llm
from dashboard.alerts import render_alerts
from dashboard.briefing import render_briefing
from dashboard.overview import render_overview
from dashboard.styles import inject_custom_css
from dashboard.timeline import render_timeline
from models.schemas import AssetClass, RiskLevel
from sources.market import detect_anomalies, fetch_market_data
from sources.news import fetch_news_signals
from sources.social import fetch_reddit_signals
from storage.narrative_store import (
    clear_narratives,
    init_db,
    load_active_narratives,
    match_to_prior_narratives,
    save_narrative,
)

st.set_page_config(
    page_title="Sentinel",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
)

inject_custom_css()
init_db()


# --- Sidebar ---
with st.sidebar:
    st.markdown(
        '<div style="padding: 8px 0 4px 0;">'
        '<span style="color: #00d4aa; font-size: 1.1rem; font-weight: 700; '
        'letter-spacing: 0.15em;">SENTINEL</span>'
        '<br><span style="color: #4a5568; font-size: 0.6rem; '
        'letter-spacing: 0.1em;">RISK NARRATIVE MONITOR</span>'
        "</div>",
        unsafe_allow_html=True,
    )

    st.markdown(
        '<div style="height: 1px; background: #1a2332; margin: 8px 0;"></div>',
        unsafe_allow_html=True,
    )

    page = st.radio(
        "Navigate",
        options=["Overview", "Alert Feed", "Timeline", "AI Briefing"],
        label_visibility="collapsed",
    )

    st.markdown(
        '<div style="height: 1px; background: #1a2332; margin: 8px 0;"></div>',
        unsafe_allow_html=True,
    )

    st.markdown(
        '<div class="section-header">LLM PROVIDER</div>',
        unsafe_allow_html=True,
    )
    if has_custom_llm():
        st.markdown(
            '<span class="source-chip">CUSTOM LLM ACTIVE</span>',
            unsafe_allow_html=True,
        )
    llm_provider = st.selectbox("LLM Provider", ["Cerebras (Free)", "OpenAI"],
                                label_visibility="collapsed")
    prefer_free = llm_provider == "Cerebras (Free)"

    st.markdown(
        '<div style="height: 1px; background: #1a2332; margin: 8px 0;"></div>',
        unsafe_allow_html=True,
    )

    st.markdown(
        '<div class="section-header">DATA SOURCES</div>',
        unsafe_allow_html=True,
    )
    fetch_news = st.checkbox("News (RSS)", value=True)
    fetch_market = st.checkbox("Market Data", value=True)
    fetch_social = st.checkbox("Social (Reddit)", value=True)
    custom_signals_fn = get_custom_signals()
    fetch_custom = (
        st.checkbox("Custom Data", value=True) if custom_signals_fn else False
    )

    if st.button("REFRESH SIGNALS", type="primary", use_container_width=True):
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

                old_narratives = load_active_narratives()
                clear_narratives()
                match_to_prior_narratives(narratives, old_narratives)

                for nar in narratives:
                    save_narrative(nar)
                    # Apply quantitative trend if history exists
                    trend = compute_quantitative_trend(
                        nar.id, len(nar.signals)
                    )
                    if trend:
                        nar.trend = trend
                        save_narrative(nar)

                st.success(f"Extracted {len(narratives)} risk narratives")

    st.markdown(
        '<div style="height: 1px; background: #1a2332; margin: 8px 0;"></div>',
        unsafe_allow_html=True,
    )
    narratives = load_active_narratives()

    st.markdown(
        '<div style="height: 1px; background: #1a2332; margin: 8px 0;"></div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<div class="section-header">ASSET CLASS FILTER</div>',
        unsafe_allow_html=True,
    )
    ASSET_LABELS = {
        AssetClass.EQUITIES: "Equities",
        AssetClass.FIXED_INCOME: "Fixed Income",
        AssetClass.PRIVATE_MARKETS: "Private Mkts",
        AssetClass.REAL_ESTATE: "Real Estate",
        AssetClass.COMMODITIES: "Commodities",
        AssetClass.FX: "FX",
    }
    selected_assets = st.multiselect(
        "Filter by asset class",
        options=list(AssetClass),
        default=list(AssetClass),
        format_func=lambda a: ASSET_LABELS.get(a, a.value),
        label_visibility="collapsed",
    )
    if selected_assets:
        asset_set = set(selected_assets)
        narratives = [
            n for n in narratives
            if asset_set & set(n.affected_assets)
        ]

    st.markdown(
        f'<div class="text-muted" style="text-align: center;">'
        f"{len(narratives)} ACTIVE NARRATIVES</div>",
        unsafe_allow_html=True,
    )


# --- Header Bar ---
highest_risk = "NONE"
risk_color = "#4a5568"
if narratives:
    risk_order = [RiskLevel.CRITICAL, RiskLevel.HIGH, RiskLevel.MEDIUM, RiskLevel.LOW]
    for level in risk_order:
        if any(n.risk_level == level for n in narratives):
            highest_risk = level.value.upper()
            colors = {
                "CRITICAL": "#FF1744",
                "HIGH": "#FF9100",
                "MEDIUM": "#FFEA00",
                "LOW": "#00E676",
            }
            risk_color = colors.get(highest_risk, "#4a5568")
            break

now_str = datetime.now().strftime("%Y-%m-%d %H:%M")

st.markdown(
    '<div class="sentinel-header">'
    "<div>"
    '<div class="sentinel-title">'
    '<span class="pulse-dot"></span>'
    '<span style="text-decoration:none !important;">SENTINEL</span>'
    "</div>"
    '<div class="sentinel-subtitle">AI-Powered Risk Narrative Monitor</div>'
    "</div>"
    "</div>",
    unsafe_allow_html=True,
)

# Metrics row
m1, m2, m3 = st.columns(3)
with m1:
    st.markdown(
        '<div class="metric-box">'
        f'<div class="metric-value">{len(narratives)}</div>'
        '<div class="metric-label">Active Narratives</div>'
        "</div>",
        unsafe_allow_html=True,
    )
with m2:
    st.markdown(
        '<div class="metric-box">'
        f'<div class="metric-value" style="color: {risk_color};">'
        f"{highest_risk}</div>"
        '<div class="metric-label">Highest Risk</div>'
        "</div>",
        unsafe_allow_html=True,
    )
with m3:
    st.markdown(
        '<div class="metric-box">'
        f'<div class="metric-value" style="font-size: 0.95rem;">{now_str}</div>'
        '<div class="metric-label">Last Refresh</div>'
        "</div>",
        unsafe_allow_html=True,
    )


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
