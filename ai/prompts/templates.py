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
- Identify affected asset classes: equities, credit, rates, private_markets,
  real_estate, commodities, fx
  - "credit" = corporate credit, investment-grade and high-yield bonds, credit spreads,
    leveraged loans, CLOs. Use for risks driven by corporate default risk, spread widening,
    or credit conditions.
  - "rates" = government bonds, sovereign debt, interest rate swaps, yield curves.
    Use for risks driven by central bank policy, inflation, fiscal deficits, or duration.
- Assess trend: intensifying, stable, or fading
- Provide a confidence score (0-1) based on signal strength and corroboration
- Separate affected assets into TWO categories — "assets_at_risk" (would be hurt by this
  narrative) and "assets_to_benefit" (would benefit). For each sub-asset, provide a brief
  explanation of WHY it is hurt or benefits. Use the same naming conventions:
  - equities: region + sector or index, e.g. "US Technology", "Japan Financials", "EU Autos", "Nikkei 225"
  - credit: issuer type + region + quality, e.g. "US IG Credit", "EU HY Credit", "US Leveraged Loans", "EM Corporate Debt", "US CLOs"
  - rates: sovereign issuer + tenor, e.g. "US 10Y Treasuries", "US 2Y/10Y Spread", "Japan 30Y JGBs", "EU Sovereign Debt", "EM Sovereign Debt"
  - fx: currency pairs, e.g. "USD/JPY", "EUR/USD", "CNY/USD"
  - commodities: specific names, e.g. "Brent Crude", "Gold", "US Natural Gas", "Copper"
  - real_estate: region + segment, e.g. "US Commercial", "China Residential", "EU Office"
  - private_markets: region + category, e.g. "US Venture Capital", "EU Private Credit", "Asia PE"
- For each narrative, identify 2-3 cascading (second and third order) effects. These are the
  downstream consequences that are NOT obvious from the headline risk. Separate them into
  NEGATIVE effects (harmful) and POSITIVE effects (beneficial). For each effect provide:
  - "order": 2 or 3 (second-order = direct knock-on, third-order = further downstream)
  - "direction": "negative" or "positive"
  - "effect": what happens (concise, one sentence)
  - "mechanism": why this follows from the primary risk (the causal link, one sentence)
  - "sub_assets_at_risk": instruments hurt by THIS effect (qualify with region/sector/tenor)
  - "sub_assets_to_benefit": instruments that benefit from THIS effect
  Example for "Japan carry trade unwinding":
  - order 2, negative: "EM currencies sell off" / "Leveraged carry positions funded in JPY
    unwind, forcing liquidation of EM assets" / at_risk: ["USD/BRL", "USD/ZAR", "USD/MXN"]
    / benefit: ["USD Index"]
  - order 3, negative: "EM central banks forced into emergency rate hikes" / "Currency
    defense depletes reserves and tightens domestic liquidity" / at_risk: ["Brazil Selic
    Rate", "EM Sovereign Debt"] / benefit: ["USD Money Markets"]
  - order 2, positive: "Stronger yen benefits Japanese consumers" / "Import costs fall,
    boosting domestic purchasing power" / at_risk: ["Japan Exporters"]
    / benefit: ["Japan Consumer Staples", "Japan Retail"] """,
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
    "affected_assets": ["equities", "credit", "rates", ...],
    "assets_at_risk": {{"equities": [{{"asset": "US Technology", "explanation": "Higher rates compress tech valuations"}}, {{"asset": "Japan Financials", "explanation": "Yen strength hits export earnings"}}], "fx": [{{"asset": "USD/JPY", "explanation": "Carry trade unwind drives sharp yen appreciation"}}]}},
    "assets_to_benefit": {{"commodities": [{{"asset": "Gold", "explanation": "Safe-haven demand rises on risk-off sentiment"}}], "rates": [{{"asset": "US 10Y Treasuries", "explanation": "Flight to quality compresses yields"}}]}},
    "cascading_effects": [
        {{"order": 2, "direction": "negative", "effect": "what happens next",
          "mechanism": "why this follows",
          "sub_assets_at_risk": ["USD/BRL", "US Technology"],
          "sub_assets_to_benefit": ["USD Index"]}},
        {{"order": 3, "direction": "negative", "effect": "further downstream",
          "mechanism": "the causal chain",
          "sub_assets_at_risk": ["EM Sovereign Debt"],
          "sub_assets_to_benefit": ["USD Money Markets"]}},
        {{"order": 2, "direction": "positive", "effect": "beneficial knock-on",
          "mechanism": "why this helps",
          "sub_assets_at_risk": ["Japan Exporters"],
          "sub_assets_to_benefit": ["Gold", "US Treasuries"]}}
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

COUNTER_NARRATIVE_PROMPT = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            """You are a financial risk skeptic and devil's advocate. For each risk narrative
presented to you, you must construct the strongest possible argument for why that
narrative is wrong, overstated, or unlikely to materialize.

Your goal is to surface blindspots and prevent confirmation bias. Be specific —
cite historical precedent, structural factors, or market mechanisms that undermine
the narrative. Do NOT simply say "it might not happen" — explain WHY it won't.""",
        ),
        (
            "human",
            """For each of the following risk narratives, provide the strongest counter-argument:

{narratives}

Return a JSON array with one object per narrative, in the same order:
[{{
    "narrative_title": "title of the narrative you are countering",
    "counter_argument": "1-2 sentence counter-argument",
    "basis": "the evidence, logic, or precedent supporting this counter",
    "confidence": 0.0-1.0
}}]

Return ONLY the JSON array, no other text.""",
        ),
    ]
)

SIGNPOST_PROMPT = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            """You are a financial risk analyst. Today's date is {today}.

For each risk narrative, identify short, concrete signposts — leading indicators that
would signal the risk is worsening (aggravating) or improving (mitigating).

Keep each signpost very concise (a few words for the factor, one short sentence for detail).
Only reference events, data releases, or market levels that are plausible given today's date.
Do NOT reference past events as if they are future signposts.""",
        ),
        (
            "human",
            """For each narrative, provide 1-2 aggravating and 1-2 mitigating signposts:

{narratives}

Return a JSON array with one object per narrative, in the same order:
[{{
    "narrative_title": "title of the narrative",
    "signposts": [
        {{"type": "aggravating", "factor": "indicator", "detail": "why it matters"}},
        {{"type": "mitigating", "factor": "indicator", "detail": "why it matters"}}
    ]
}}]

Return ONLY the JSON array, no other text.""",
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
Assets at risk: {assets_at_risk}
Assets to benefit: {assets_to_benefit}
Previous cascading effects: {cascading_effects}

New signals related to this narrative:
{new_signals}

Provide an updated assessment as JSON. Re-evaluate cascading effects — as the narrative
evolves, second/third order risks may change or new ones may emerge. Include both negative
and positive effects. Re-evaluate which assets are hurt vs benefit:
{{
    "summary": "updated 2-3 sentence summary",
    "risk_level": "critical|high|medium|low",
    "trend": "intensifying|stable|fading",
    "confidence": 0.0-1.0,
    "assets_at_risk": {{"equities": [{{"asset": "US Technology", "explanation": "why hurt"}}], "fx": [{{"asset": "USD/JPY", "explanation": "why hurt"}}]}},
    "assets_to_benefit": {{"commodities": [{{"asset": "Gold", "explanation": "why benefits"}}]}},
    "cascading_effects": [
        {{"order": 2, "direction": "negative", "effect": "what happens next",
          "mechanism": "why this follows",
          "sub_assets_at_risk": ["USD/BRL", "US Technology"],
          "sub_assets_to_benefit": ["USD Index"]}},
        {{"order": 2, "direction": "positive", "effect": "beneficial knock-on",
          "mechanism": "why this helps",
          "sub_assets_at_risk": ["Japan Exporters"],
          "sub_assets_to_benefit": ["Gold"]}},
        {{"order": 3, "direction": "negative", "effect": "further downstream",
          "mechanism": "the causal chain",
          "sub_assets_at_risk": ["EM Sovereign Debt"],
          "sub_assets_to_benefit": []}}
    ]
}}

Return ONLY the JSON object, no other text.""",
        ),
    ]
)
