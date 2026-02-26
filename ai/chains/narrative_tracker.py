"""Track and update existing narratives with new signals."""

import json
from datetime import datetime

from langchain_core.language_models import BaseChatModel

from ai.chains.trend_analyzer import compute_quantitative_trend
from ai.prompts.templates import NARRATIVE_UPDATE_PROMPT
from models.schemas import AssetClass, CascadingEffect, Narrative, RiskLevel, Signal


def update_narrative(
    narrative: Narrative, new_signals: list[Signal], llm: BaseChatModel
) -> Narrative:
    """Update an existing narrative with new signal data."""
    if not new_signals:
        return narrative

    signal_text = "\n\n".join(
        f"[{s.id}] ({s.source.value}) {s.title}\n{s.content[:300]}" for s in new_signals
    )

    chain = NARRATIVE_UPDATE_PROMPT | llm
    response = chain.invoke(
        {
            "title": narrative.title,
            "summary": narrative.summary,
            "risk_level": narrative.risk_level.value,
            "trend": narrative.trend,
            "affected_assets": ", ".join(a.value for a in narrative.affected_assets),
            "asset_detail": json.dumps(
                {a.value: subs for a, subs in narrative.asset_detail.items()}
            ),
            "cascading_effects": json.dumps(
                [e.model_dump() for e in narrative.cascading_effects]
            ),
            "new_signals": signal_text,
        }
    )

    try:
        raw = response.content
        if "```" in raw:
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        update = json.loads(raw.strip())
    except (json.JSONDecodeError, IndexError):
        return narrative

    narrative.summary = update.get("summary", narrative.summary)
    narrative.risk_level = RiskLevel(update.get("risk_level", narrative.risk_level.value))
    narrative.trend = update.get("trend", narrative.trend)
    narrative.confidence = update.get("confidence", narrative.confidence)

    # Parse updated asset_detail from LLM response
    raw_detail = update.get("asset_detail", {})
    if isinstance(raw_detail, dict) and raw_detail:
        asset_detail: dict[AssetClass, list[str]] = {}
        for key, subs in raw_detail.items():
            try:
                ac = AssetClass(key)
            except ValueError:
                continue
            if isinstance(subs, list):
                asset_detail[ac] = [str(s) for s in subs]
        narrative.asset_detail = asset_detail

    # Parse updated cascading effects
    raw_effects = update.get("cascading_effects", [])
    if isinstance(raw_effects, list) and raw_effects:
        cascading_effects: list[CascadingEffect] = []
        for eff in raw_effects:
            if isinstance(eff, dict) and "effect" in eff and "mechanism" in eff:
                cascading_effects.append(
                    CascadingEffect(
                        order=int(eff.get("order", 2)),
                        effect=eff["effect"],
                        mechanism=eff["mechanism"],
                    )
                )
        narrative.cascading_effects = cascading_effects

    narrative.signals.extend(new_signals)
    narrative.last_updated = datetime.utcnow()

    # Override LLM trend with quantitative analysis when history exists
    quant_trend = compute_quantitative_trend(narrative.id, len(narrative.signals))
    if quant_trend:
        narrative.trend = quant_trend

    return narrative
