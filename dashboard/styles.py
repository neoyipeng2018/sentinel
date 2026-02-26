"""Global CSS injection for command-center UI aesthetic."""

import streamlit as st

CUSTOM_CSS = """
<style>
/* === BASE TYPOGRAPHY === */
*, .stMarkdown, .stText, p, span, div, li, td, th, label, .stSelectbox, .stMultiSelect {
    font-family: 'SF Mono', 'Cascadia Code', 'Consolas', 'Fira Code', monospace !important;
}

h1, h2, h3, h4, h5, h6 {
    font-family: 'SF Mono', 'Cascadia Code', 'Consolas', monospace !important;
    letter-spacing: 0.05em;
    text-transform: uppercase;
}

/* === HIDE DEFAULT STREAMLIT CHROME === */
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
header[data-testid="stHeader"] {
    background-color: #0a0e14 !important;
    height: 0px !important;
    min-height: 0px !important;
    padding: 0 !important;
}

/* === MAIN CONTAINER === */
.stApp {
    background-color: #0a0e14;
}

section[data-testid="stSidebar"] {
    background-color: #0d1117 !important;
    border-right: 1px solid #1a2332 !important;
}

section[data-testid="stSidebar"] .stMarkdown h1 {
    font-size: 1.1rem;
    color: #00d4aa;
}

/* === COMPACT SPACING === */
.block-container {
    padding-top: 1rem !important;
    padding-bottom: 0 !important;
}

div[data-testid="stVerticalBlock"] > div {
    gap: 0.4rem;
}

/* === SCROLLBAR === */
::-webkit-scrollbar {
    width: 6px;
    height: 6px;
}
::-webkit-scrollbar-track {
    background: #0a0e14;
}
::-webkit-scrollbar-thumb {
    background: #1a2332;
    border-radius: 3px;
}
::-webkit-scrollbar-thumb:hover {
    background: #2a3442;
}

/* === PANEL CARD === */
.cmd-panel {
    background: #1a1f2e;
    border: 1px solid #1a2332;
    border-radius: 6px;
    padding: 16px;
    margin-bottom: 8px;
    transition: border-color 0.2s ease;
}
.cmd-panel:hover {
    border-color: #2a3442;
}

/* === RISK LEVEL PANELS === */
.cmd-panel-critical {
    border-left: 3px solid #FF1744;
    box-shadow: inset 0 0 20px rgba(255, 23, 68, 0.05);
}
.cmd-panel-high {
    border-left: 3px solid #FF9100;
    box-shadow: inset 0 0 20px rgba(255, 145, 0, 0.05);
}
.cmd-panel-medium {
    border-left: 3px solid #FFEA00;
}
.cmd-panel-low {
    border-left: 3px solid #00E676;
}

/* === SEVERITY BADGES === */
.badge {
    display: inline-block;
    padding: 2px 8px;
    border-radius: 3px;
    font-size: 0.65rem;
    font-weight: 700;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    font-family: 'SF Mono', 'Cascadia Code', monospace !important;
}
.badge-critical {
    background: rgba(255, 23, 68, 0.2);
    color: #FF1744;
    border: 1px solid rgba(255, 23, 68, 0.3);
}
.badge-high {
    background: rgba(255, 145, 0, 0.2);
    color: #FF9100;
    border: 1px solid rgba(255, 145, 0, 0.3);
}
.badge-medium {
    background: rgba(255, 234, 0, 0.2);
    color: #FFEA00;
    border: 1px solid rgba(255, 234, 0, 0.3);
}
.badge-low {
    background: rgba(0, 230, 118, 0.2);
    color: #00E676;
    border: 1px solid rgba(0, 230, 118, 0.3);
}

/* === SOURCE CHIPS === */
.source-chip {
    display: inline-block;
    padding: 1px 6px;
    border-radius: 3px;
    font-size: 0.6rem;
    font-weight: 600;
    letter-spacing: 0.05em;
    text-transform: uppercase;
    background: rgba(0, 212, 170, 0.1);
    color: #00d4aa;
    border: 1px solid rgba(0, 212, 170, 0.2);
}

/* === PULSE DOT === */
@keyframes pulse {
    0% { box-shadow: 0 0 0 0 rgba(0, 230, 118, 0.7); }
    70% { box-shadow: 0 0 0 6px rgba(0, 230, 118, 0); }
    100% { box-shadow: 0 0 0 0 rgba(0, 230, 118, 0); }
}
.pulse-dot {
    display: inline-block;
    width: 8px;
    height: 8px;
    border-radius: 50%;
    background: #00E676;
    animation: pulse 2s infinite;
    margin-right: 8px;
    vertical-align: middle;
}

/* === HEADER BAR === */
.sentinel-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 12px 0;
    border-bottom: 1px solid #1a2332;
    margin-bottom: 16px;
}
.sentinel-title {
    font-size: 1.4rem;
    font-weight: 700;
    color: #e0e4ec;
    letter-spacing: 0.15em;
    display: flex;
    align-items: center;
    gap: 8px;
    text-decoration: none !important;
}
.sentinel-title * {
    text-decoration: none !important;
}
.sentinel-subtitle {
    font-size: 0.65rem;
    color: #4a5568;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    margin-top: 2px;
}

/* === METRICS ROW === */
.metric-box {
    background: #1a1f2e;
    border: 1px solid #1a2332;
    border-radius: 4px;
    padding: 8px 14px;
    text-align: center;
}
.metric-value {
    font-size: 1.4rem;
    font-weight: 700;
    color: #e0e4ec;
}
.metric-label {
    font-size: 0.6rem;
    color: #4a5568;
    text-transform: uppercase;
    letter-spacing: 0.1em;
}

/* === SVG GAUGE === */
.gauge-container {
    display: flex;
    flex-direction: column;
    align-items: center;
    padding: 8px 0;
}
.gauge-label {
    font-size: 0.7rem;
    color: #8892a4;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    margin-top: 4px;
}

/* === TREND INDICATORS === */
.trend-up { color: #FF1744; }
.trend-stable { color: #FFEA00; }
.trend-down { color: #00E676; }

/* === SIGNAL ROW === */
.signal-row {
    padding: 10px 14px;
    border-bottom: 1px solid #111827;
    display: flex;
    align-items: flex-start;
    gap: 10px;
}
.signal-row:hover {
    background: rgba(26, 31, 46, 0.5);
}
.signal-dot {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    margin-top: 6px;
    flex-shrink: 0;
}
.signal-meta {
    font-size: 0.7rem;
    color: #4a5568;
    margin-top: 2px;
}

/* === BRIEFING PANEL === */
.briefing-panel {
    background: #1a1f2e;
    border: 1px solid #1a2332;
    border-radius: 6px;
    padding: 20px 24px;
}
.briefing-header {
    font-size: 0.7rem;
    color: #4a5568;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    border-bottom: 1px solid #1a2332;
    padding-bottom: 8px;
    margin-bottom: 16px;
}
.briefing-text {
    color: #c5c8d4;
    line-height: 1.7;
    font-size: 0.9rem;
}

/* === EXPANDER OVERRIDE === */
details[data-testid="stExpander"] {
    background: #1a1f2e !important;
    border: 1px solid #1a2332 !important;
    border-radius: 6px !important;
}

/* === BUTTONS === */
.stButton > button[kind="primary"] {
    background: rgba(0, 212, 170, 0.15) !important;
    color: #00d4aa !important;
    border: 1px solid rgba(0, 212, 170, 0.3) !important;
    font-family: 'SF Mono', monospace !important;
    letter-spacing: 0.05em;
    text-transform: uppercase;
    font-size: 0.75rem;
}
.stButton > button[kind="primary"]:hover {
    background: rgba(0, 212, 170, 0.25) !important;
    border-color: rgba(0, 212, 170, 0.5) !important;
}

/* === SELECTBOX / INPUTS === */
div[data-baseweb="select"] {
    background: #1a1f2e !important;
}
div[data-baseweb="select"] > div {
    background: #1a1f2e !important;
    border-color: #1a2332 !important;
}

/* === CRITICAL GLOW === */
@keyframes criticalGlow {
    0%, 100% { box-shadow: 0 0 5px rgba(255, 23, 68, 0.1); }
    50% { box-shadow: 0 0 15px rgba(255, 23, 68, 0.2); }
}
.glow-critical {
    animation: criticalGlow 3s ease-in-out infinite;
}

/* === CASCADING EFFECTS === */
.cascade-chain {
    margin-top: 10px;
    padding: 10px 12px;
    background: rgba(0, 212, 170, 0.03);
    border: 1px solid rgba(0, 212, 170, 0.1);
    border-radius: 4px;
}
.cascade-header {
    font-size: 0.6rem;
    color: #00d4aa;
    letter-spacing: 0.12em;
    margin-bottom: 8px;
    font-weight: 700;
}
.cascade-row {
    display: flex;
    align-items: flex-start;
    gap: 8px;
    margin-bottom: 6px;
}
.cascade-row:last-child {
    margin-bottom: 0;
}
.cascade-order {
    flex-shrink: 0;
    font-size: 0.6rem;
    font-weight: 700;
    color: #00d4aa;
    background: rgba(0, 212, 170, 0.1);
    border: 1px solid rgba(0, 212, 170, 0.2);
    border-radius: 3px;
    padding: 1px 5px;
    min-width: 28px;
    text-align: center;
}
.cascade-connector {
    flex-shrink: 0;
    width: 12px;
    border-top: 1px dashed #2a3442;
    margin-top: 8px;
}
.cascade-effect {
    color: #c5c8d4;
    font-size: 0.78rem;
    line-height: 1.4;
}
.cascade-mechanism {
    color: #4a5568;
    font-size: 0.7rem;
    font-style: italic;
    line-height: 1.4;
    margin-top: 1px;
}

/* === MUTED TEXT === */
.text-muted {
    color: #4a5568;
    font-size: 0.75rem;
}

/* === SECTION HEADER === */
.section-header {
    font-size: 0.7rem;
    color: #4a5568;
    letter-spacing: 0.15em;
    text-transform: uppercase;
    padding-bottom: 8px;
    border-bottom: 1px solid #1a2332;
    margin-bottom: 12px;
    display: flex;
    align-items: center;
    gap: 6px;
}
</style>
"""


def inject_custom_css() -> None:
    """Inject the global custom CSS into the Streamlit app."""
    st.markdown(CUSTOM_CSS, unsafe_allow_html=True)
