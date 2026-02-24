# Sentinel

AI-powered financial risk narrative monitor. Ingests signals from news RSS feeds, market data (yfinance), and social media (Reddit), then uses LLMs to cluster them into **risk narratives** — thematic stories about developing risks to financial markets (e.g., "Japan carry trade unwinding", "CRE distress spreading to regional banks"). Tracks how narratives evolve over time.

## Quick Start

```bash
poetry install
cp .env.example .env   # add your OPENAI_API_KEY and/or CEREBRAS_API_KEY
poetry run streamlit run app.py
```

## Architecture

```
Sources (news, market, social, custom)
  → Signals
    → LLM narrative extraction
      → Storage (SQLite)
        → Streamlit dashboard
```

| Directory | What it does |
|-----------|-------------|
| `sources/` | Data ingestion — each module returns `list[Signal]` |
| `ai/` | LangChain LLM pipeline — narrative extraction, tracking, risk scoring, briefings |
| `models/` | Pydantic schemas (`Signal`, `Narrative`, `RiskBriefing`) |
| `storage/` | SQLite persistence with narrative history |
| `dashboard/` | Streamlit UI pages (overview, alerts, timeline, briefing) |
| `config/` | Settings, local overrides |

## Customization

All customization lives in a single file: **`config/local_config.py`**. This file is git-ignored so your changes won't conflict with upstream updates.

```bash
cp config/local_config.example.py config/local_config.py
```

Then uncomment and edit the sections you need. See below.

---

### Bring Your Own LLM

Define a `custom_llm_factory` function that returns any LangChain `BaseChatModel`. Sentinel will try your LLM first and fall back to Cerebras/OpenAI if it fails.

**Ollama (local)**
```python
# config/local_config.py
from langchain_ollama import ChatOllama

def custom_llm_factory(**kwargs):
    return ChatOllama(model="llama3", temperature=0.3, **kwargs)
```

**vLLM (local)**
```python
from langchain_openai import ChatOpenAI

def custom_llm_factory(**kwargs):
    return ChatOpenAI(
        base_url="http://localhost:8000/v1",
        api_key="not-needed",
        model="meta-llama/Llama-3-8b",
        temperature=0.3,
        **kwargs,
    )
```

**OpenRouter**
```python
from langchain_openai import ChatOpenAI

def custom_llm_factory(**kwargs):
    return ChatOpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key="sk-or-...",
        model="meta-llama/llama-3-70b-instruct",
        temperature=0.3,
        **kwargs,
    )
```

Any provider that has a LangChain integration works — Anthropic, Google, Groq, Together, Fireworks, etc. Just `pip install` the relevant package and return the chat model.

When a custom LLM is active, the sidebar shows "Using custom LLM from local_config.py". The built-in Cerebras/OpenAI providers stay available as automatic fallbacks.

---

### Bring Your Own Data

Define a `custom_signals` function that returns `list[Signal]`. A "Custom Data" checkbox will appear in the sidebar automatically, and your signals get fed into the same narrative extraction pipeline as everything else.

**From a CSV**
```python
# config/local_config.py
import hashlib
import pandas as pd
from datetime import datetime
from models.schemas import Signal, SignalSource

def custom_signals():
    df = pd.read_csv("my_data.csv")  # columns: title, content
    return [
        Signal(
            id=hashlib.md5(row["title"].encode()).hexdigest()[:12],
            source=SignalSource.CUSTOM,
            title=row["title"],
            content=row.get("content", row["title"]),
            timestamp=datetime.utcnow(),
        )
        for _, row in df.iterrows()
    ]
```

**From an API**
```python
import hashlib
import requests
from datetime import datetime
from models.schemas import Signal, SignalSource

def custom_signals():
    resp = requests.get("https://your-api.com/signals", timeout=10)
    return [
        Signal(
            id=hashlib.md5(item["title"].encode()).hexdigest()[:12],
            source=SignalSource.CUSTOM,
            title=item["title"],
            content=item["body"],
            timestamp=datetime.utcnow(),
        )
        for item in resp.json()
    ]
```

The `Signal` model fields:

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `id` | `str` | yes | Unique ID, typically a short hash |
| `source` | `SignalSource` | yes | Use `SignalSource.CUSTOM` |
| `title` | `str` | yes | Short headline |
| `content` | `str` | yes | Full text for LLM analysis |
| `url` | `str` | no | Link to source |
| `timestamp` | `datetime` | no | Defaults to now |
| `metadata` | `dict` | no | Any extra fields |

---

### Override Built-in Data Sources

You can also replace the default watchlists, subreddits, and RSS feeds:

```python
# config/local_config.py

# Market tickers to monitor (dict of asset class -> symbols)
WATCHLIST = {
    "equities": ["^GSPC", "^IXIC", "AAPL", "TSLA"],
    "commodities": ["GC=F", "CL=F"],
}

# Z-score threshold for anomaly detection (lower = more sensitive)
Z_SCORE_THRESHOLD = 1.5

# Subreddits to monitor
SUBREDDITS = ["wallstreetbets", "investing", "economics"]

# RSS feeds
NEWS_FEEDS = [
    "https://feeds.reuters.com/reuters/businessNews",
    "https://feeds.bbci.co.uk/news/business/rss.xml",
]
```

---

## Development

```bash
poetry run ruff check .           # lint
poetry run ruff check . --fix     # autofix
poetry run pytest                 # tests
poetry run mypy .                 # type check
```
