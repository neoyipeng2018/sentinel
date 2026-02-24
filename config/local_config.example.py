"""
Local configuration overrides for Sentinel.

Copy this file to config/local_config.py and uncomment the sections you want.
local_config.py is git-ignored so your settings won't cause merge conflicts.
"""

# ---------------------------------------------------------------------------
# Custom LLM provider
# ---------------------------------------------------------------------------
# Return any LangChain BaseChatModel. Sentinel will use this instead of
# Cerebras/OpenAI when defined.
#
# --- Ollama (local) ---
# from langchain_ollama import ChatOllama
# def custom_llm_factory(**kwargs):
#     return ChatOllama(model="llama3", temperature=0.3, **kwargs)
#
# --- vLLM (local) ---
# from langchain_openai import ChatOpenAI
# def custom_llm_factory(**kwargs):
#     return ChatOpenAI(
#         base_url="http://localhost:8000/v1",
#         api_key="not-needed",
#         model="meta-llama/Llama-3-8b",
#         temperature=0.3,
#         **kwargs,
#     )
#
# --- OpenRouter ---
# from langchain_openai import ChatOpenAI
# def custom_llm_factory(**kwargs):
#     return ChatOpenAI(
#         base_url="https://openrouter.ai/api/v1",
#         api_key="sk-or-...",
#         model="meta-llama/llama-3-70b-instruct",
#         temperature=0.3,
#         **kwargs,
#     )

# ---------------------------------------------------------------------------
# Market watchlist — dict of asset class -> ticker symbols
# ---------------------------------------------------------------------------
# WATCHLIST = {
#     "equities": ["^GSPC", "^IXIC", "^DJI", "^VIX", "^RUT"],
#     "fixed_income": ["^TNX", "^TYX", "^FVX", "TLT", "HYG", "LQD"],
#     "commodities": ["GC=F", "CL=F", "SI=F"],
#     "fx": ["DX-Y.NYB", "EURUSD=X", "JPYUSD=X"],
#     "real_estate": ["VNQ", "IYR", "XLRE"],
# }

# ---------------------------------------------------------------------------
# Z-score threshold for anomaly detection (lower = more sensitive)
# ---------------------------------------------------------------------------
# Z_SCORE_THRESHOLD = 2.0

# ---------------------------------------------------------------------------
# Subreddits to monitor
# ---------------------------------------------------------------------------
# SUBREDDITS = [
#     "wallstreetbets",
#     "investing",
#     "economics",
#     "stocks",
#     "bonds",
#     "RealEstate",
#     "CryptoCurrency",
# ]

# ---------------------------------------------------------------------------
# RSS news feeds
# ---------------------------------------------------------------------------
# NEWS_FEEDS = [
#     "https://feeds.reuters.com/reuters/businessNews",
#     "https://feeds.bbci.co.uk/news/business/rss.xml",
#     "https://www.cnbc.com/id/100003114/device/rss/rss.html",
# ]

# ---------------------------------------------------------------------------
# Custom data source
# ---------------------------------------------------------------------------
# Define a function that returns list[Signal] to plug in your own data.
# It shows up as a "Custom Data" checkbox in the sidebar.
#
# --- Example: load signals from a CSV file ---
# import hashlib
# import pandas as pd
# from datetime import datetime
# from models.schemas import Signal, SignalSource
#
# def custom_signals():
#     df = pd.read_csv("my_data.csv")  # columns: title, content, url (optional)
#     signals = []
#     for _, row in df.iterrows():
#         sig_id = hashlib.md5(row["title"].encode()).hexdigest()[:12]
#         signals.append(Signal(
#             id=sig_id,
#             source=SignalSource.CUSTOM,
#             title=row["title"],
#             content=row.get("content", row["title"]),
#             url=row.get("url", ""),
#             timestamp=datetime.utcnow(),
#         ))
#     return signals
#
# --- Example: fetch from a custom API ---
# import requests
# import hashlib
# from datetime import datetime
# from models.schemas import Signal, SignalSource
#
# def custom_signals():
#     resp = requests.get("https://your-api.com/signals", timeout=10)
#     return [
#         Signal(
#             id=hashlib.md5(item["title"].encode()).hexdigest()[:12],
#             source=SignalSource.CUSTOM,
#             title=item["title"],
#             content=item["body"],
#             timestamp=datetime.utcnow(),
#         )
#         for item in resp.json()
#     ]
