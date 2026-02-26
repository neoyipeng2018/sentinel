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
- Identify affected asset classes: equities, fixed_income, private_markets,
  real_estate, commodities, fx
- Assess trend: intensifying, stable, or fading
- Provide a confidence score (0-1) based on signal strength and corroboration
- For each affected asset class, list specific sub-assets in an "asset_detail" object keyed
  by asset class. Qualify with country/region where relevant:
  - equities: region + sector or index, e.g. "US Technology", "Japan Financials", "EU Autos", "Nikkei 225"
  - fixed_income: issuer type + region + tenor where relevant, e.g. "US 10Y Treasuries", "US 2Y/10Y Spread", "EU IG Credit", "EM Sovereign Debt", "Japan 30Y JGBs"
  - fx: currency pairs, e.g. "USD/JPY", "EUR/USD", "CNY/USD"
  - commodities: specific names, e.g. "Brent Crude", "Gold", "US Natural Gas", "Copper"
  - real_estate: region + segment, e.g. "US Commercial", "China Residential", "EU Office"
  - private_markets: region + category, e.g. "US Venture Capital", "EU Private Credit", "Asia PE"
- For each narrative, identify 2-3 cascading (second and third order) effects. These are the
  downstream consequences that are NOT obvious from the headline risk. For each effect provide:
  - "order": 2 or 3 (second-order = direct knock-on, third-order = further downstream)
  - "effect": what happens (concise, one sentence)
  - "mechanism": why this follows from the primary risk (the causal link, one sentence)
  - "affected_sub_assets": specific instruments/sub-assets impacted by THIS effect (same
    naming convention as asset_detail — qualify with region/sector/tenor)
  Example for "Japan carry trade unwinding":
  - order 2: "EM currencies sell off" / "Leveraged carry positions funded in JPY unwind, forcing liquidation of EM assets" / ["USD/BRL", "USD/ZAR", "USD/MXN"]
  - order 3: "EM central banks forced into emergency rate hikes" / "Currency defense depletes reserves and tightens domestic liquidity" / ["Brazil Selic Rate", "South Africa Repo Rate", "EM Sovereign Debt"] """,
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
    "asset_detail": {{"equities": ["US Technology", "Japan Financials"], "fx": ["USD/JPY"], "fixed_income": ["US Treasuries"]}},
    "cascading_effects": [
        {{"order": 2, "effect": "what happens next", "mechanism": "why this follows", "affected_sub_assets": ["USD/BRL", "US Technology"]}},
        {{"order": 3, "effect": "further downstream impact", "mechanism": "the causal chain", "affected_sub_assets": ["EM Sovereign Debt"]}}
    ],
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
Affected assets: {affected_assets}
Sub-asset detail: {asset_detail}
Previous cascading effects: {cascading_effects}

New signals related to this narrative:
{new_signals}

Provide an updated assessment as JSON. Re-evaluate cascading effects — as the narrative
evolves, second/third order risks may change or new ones may emerge:
{{
    "summary": "updated 2-3 sentence summary",
    "risk_level": "critical|high|medium|low",
    "trend": "intensifying|stable|fading",
    "confidence": 0.0-1.0,
    "asset_detail": {{"equities": ["US Technology", "Japan Financials"], "fx": ["USD/JPY"]}},
    "cascading_effects": [
        {{"order": 2, "effect": "what happens next", "mechanism": "why this follows", "affected_sub_assets": ["USD/BRL", "US Technology"]}},
        {{"order": 3, "effect": "further downstream impact", "mechanism": "the causal chain", "affected_sub_assets": ["EM Sovereign Debt"]}}
    ]
}}

Return ONLY the JSON object, no other text.""",
        ),
    ]
)
