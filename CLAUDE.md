# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What is Sentinel

AI-powered financial risk narrative monitor. Ingests signals from news RSS feeds, market data (yfinance/FRED), and social media (Reddit), then uses LLMs to synthesize them into coherent **risk narratives** — thematic stories about developing risks to financial markets (e.g., "Japan carry trade unwinding", "CRE distress spreading to regional banks"). Tracks how narratives evolve over time.

## Commands

```bash
# Setup
poetry install
cp .env.example .env  # Then fill in API keys

# Run the app
poetry run streamlit run app.py

# Tests
poetry run pytest
poetry run pytest tests/test_schemas.py -v  # Single test file

# Linting
poetry run ruff check .
poetry run ruff check . --fix
poetry run mypy .
```

## Architecture

**Data flow:** Sources → Signals → LLM Narrative Extraction → Storage → Dashboard

- `sources/` — Data ingestion. Each module returns `list[Signal]`:
  - `news.py` — RSS feed aggregator (feedparser)
  - `market.py` — yfinance + anomaly detection via z-score on daily returns
  - `social.py` — Reddit public JSON API (no auth required for read)

- `ai/` — LangChain-powered LLM pipeline:
  - `llm.py` — Provider setup. Cerebras (free/fast) as default, OpenAI as fallback. Both via LangChain.
  - `chains/narrative_extractor.py` — Takes raw signals, LLM clusters them into named `Narrative` objects
  - `chains/narrative_tracker.py` — Updates existing narratives with new signals
  - `chains/risk_assessor.py` — Scores risk per asset class (pure Python, no LLM)
  - `chains/briefing_generator.py` — Generates natural language risk briefings
  - `prompts/templates.py` — All LangChain prompt templates in one place

- `models/schemas.py` — Pydantic models: `Signal`, `Narrative`, `RiskBriefing`, plus enums for `RiskLevel`, `AssetClass`, `SignalSource`

- `storage/narrative_store.py` — SQLite persistence with narrative history tracking for timeline view

- `dashboard/` — Streamlit UI pages: `overview.py` (risk heatmap), `alerts.py` (signal feed), `timeline.py` (narrative evolution), `briefing.py` (AI briefing)

- `app.py` — Streamlit entry point. Wires sidebar controls to data fetching, narrative extraction, and page routing.

## LLM Providers

- **Cerebras** (`langchain-cerebras`): Free inference, Llama 3.3 70B. Default for all chains.
- **OpenAI** (`langchain-openai`): gpt-4o-mini. Fallback or for higher quality.
- Provider selection is in the sidebar at runtime. Code-level: `get_llm(prefer_free=True)`.

## Key Design Decisions

- LLM responses for narrative extraction are JSON. Prompts instruct "return ONLY the JSON array". Parsing handles markdown-wrapped code blocks.
- Narrative history is snapshot-based: each update inserts a row in `narrative_history` for the timeline chart.
- Market anomaly detection uses rolling 20-day z-scores (threshold: 2.0 std devs).
- All chains use `prompt | llm` composition (LangChain LCEL).
