"""Prompt templates for the AI pipeline."""

from langchain_core.prompts import ChatPromptTemplate

NARRATIVE_EXTRACTION_PROMPT = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            """You are a financial risk analyst. Your job is to identify emerging risk narratives
from a batch of signals (news headlines, market data anomalies, social media posts).

A "risk narrative" is a coherent thematic story about a developing risk to financial markets.
Examples: "US regional bank stress spreading", "China property sector contagion",
"AI capex bubble concerns growing", "Japan carry trade unwinding".

Rules:
- Group related signals into distinct narratives
- Each narrative must have a clear, concise title
- Assess risk level: critical, high, medium, or low
- Identify affected asset classes: equities, fixed_income, macro, private_markets,
  real_estate, commodities, crypto, fx
- Assess trend: intensifying, stable, or fading
- Provide a confidence score (0-1) based on signal strength and corroboration""",
        ),
        (
            "human",
            """Analyze these signals and extract risk narratives:

{signals}

Return your analysis as a JSON array of narratives with this structure:
[{{
    "title": "narrative title",
    "summary": "2-3 sentence summary of the risk narrative",
    "risk_level": "critical|high|medium|low",
    "affected_assets": ["equities", "fixed_income", ...],
    "trend": "intensifying|stable|fading",
    "confidence": 0.0-1.0,
    "signal_ids": ["id1", "id2", ...]
}}]

Return ONLY the JSON array, no other text.""",
        ),
    ]
)

RISK_BRIEFING_PROMPT = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            """You are a senior financial risk strategist writing a risk briefing for
institutional investors. Your tone is direct, analytical, and actionable.
Focus on what matters and what could move markets.""",
        ),
        (
            "human",
            """Generate a risk briefing based on these active narratives:

{narratives}

Structure your briefing as:
1. **Executive Summary** (2-3 sentences on the overall risk landscape)
2. **Top Risks** (the most critical narratives, ranked by severity)
3. **Market Outlook** (how these narratives could affect markets near-term)
4. **Watchlist** (emerging narratives that could escalate)

Be specific. Reference data points where available. No fluff.""",
        ),
    ]
)

NARRATIVE_UPDATE_PROMPT = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            """You are tracking the evolution of a financial risk narrative over time.
Given the existing narrative and new signals, determine if and how the narrative has changed.""",
        ),
        (
            "human",
            """Existing narrative:
Title: {title}
Previous summary: {summary}
Previous risk level: {risk_level}
Previous trend: {trend}

New signals related to this narrative:
{new_signals}

Provide an updated assessment as JSON:
{{
    "summary": "updated 2-3 sentence summary",
    "risk_level": "critical|high|medium|low",
    "trend": "intensifying|stable|fading",
    "confidence": 0.0-1.0
}}

Return ONLY the JSON object, no other text.""",
        ),
    ]
)
