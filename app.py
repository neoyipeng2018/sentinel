"""Sentinel - AI-powered financial risk narrative monitor."""

from datetime import datetime

import streamlit as st

from ai.llm import get_llm
from config.overrides import get_custom_signals
from config.settings import settings
from dashboard.alerts import render_alerts
from dashboard.briefing import render_briefing
from dashboard.overview import render_overview
from dashboard.styles import inject_custom_css
from dashboard.timeline import render_timeline
from models.schemas import AssetClass, RiskLevel
from scheduler import refresh_lock, run_refresh_cycle, start_scheduler, stop_scheduler
from storage.narrative_store import init_db, load_active_narratives

st.set_page_config(
    page_title="Sentinel",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
)

inject_custom_css()
init_db()


def _run_refresh(prefer_free: bool = True) -> None:
    """Execute one manual refresh cycle using the shared lock."""
    with refresh_lock:
        count = run_refresh_cycle(prefer_free=prefer_free)
    st.session_state["last_refresh"] = datetime.now()
    st.session_state["last_refresh_count"] = count


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

    prefer_free = True

    st.markdown(
        '<div class="section-header">DATA SOURCES</div>',
        unsafe_allow_html=True,
    )
    fetch_news = st.checkbox("News (RSS)", value=True)
    fetch_market = st.checkbox("Market Data", value=True)
    fetch_social = st.checkbox("Social (Reddit)", value=True)
    fetch_predictions = st.checkbox("Predictions (Kalshi/Polymarket)", value=True)
    custom_signals_fn = get_custom_signals()
    fetch_custom = (
        st.checkbox("Custom Data", value=True) if custom_signals_fn else False
    )

    if st.button("REFRESH SIGNALS", type="primary", use_container_width=True):
        with st.spinner("Fetching signals..."):
            _run_refresh(prefer_free=prefer_free)
            count = st.session_state.get("last_refresh_count", 0)
            if count:
                st.success(f"Extracted {count} risk narratives")

    st.markdown(
        '<div style="height: 1px; background: #1a2332; margin: 8px 0;"></div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<div class="section-header">AUTO-REFRESH</div>',
        unsafe_allow_html=True,
    )
    auto_refresh = st.checkbox("Auto-refresh (hourly)", value=True)

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
        AssetClass.CREDIT: "Credit",
        AssetClass.RATES: "Rates",
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


# --- Background scheduler ---
if auto_refresh:
    start_scheduler(settings.auto_refresh_interval_minutes)
else:
    stop_scheduler()


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
    render_overview(narratives, selected_assets)
elif page == "Alert Feed":
    render_alerts(narratives)
elif page == "Timeline":
    render_timeline(narratives)
elif page == "AI Briefing":
    llm = get_llm(prefer_free=prefer_free)
    render_briefing(narratives, llm)
