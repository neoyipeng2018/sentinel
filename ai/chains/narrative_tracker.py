"""Track and update existing narratives with new signals."""

import json
from datetime import datetime

from langchain_core.language_models import BaseChatModel

from ai.chains.trend_analyzer import compute_quantitative_trend
from ai.prompts.templates import NARRATIVE_UPDATE_PROMPT
from models.schemas import AssetClass, AssetImpact, CascadingEffect, Narrative, RiskLevel, Signal


def update_narrative(
    narrative: Narrative, new_signals: list[Signal], llm: BaseChatModel
) -> Narrative:
    """Update an existing narrative with new signal data."""
    if not new_signals:
        return narrative

    signal_text = "\n\n".join(
        f"[{s.id}] ({s.source.value}) {s.title}\n{s.content[:300]}" for s in new_signals
    )

    def _serialize_impacts(d: dict[AssetClass, list[AssetImpact]]) -> str:
        return json.dumps(
            {a.value: [i.model_dump() for i in imps] for a, imps in d.items()}
        )

    chain = NARRATIVE_UPDATE_PROMPT | llm
    response = chain.invoke(
        {
            "title": narrative.title,
            "summary": narrative.summary,
            "risk_level": narrative.risk_level.value,
            "trend": narrative.trend,
            "affected_assets": ", ".join(a.value for a in narrative.affected_assets),
            "assets_at_risk": _serialize_impacts(narrative.assets_at_risk),
            "assets_to_benefit": _serialize_impacts(narrative.assets_to_benefit),
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

    # Parse updated assets_at_risk / assets_to_benefit
    from ai.chains.narrative_extractor import _parse_asset_impacts

    raw_at_risk = update.get("assets_at_risk", {})
    if isinstance(raw_at_risk, dict) and raw_at_risk:
        narrative.assets_at_risk = _parse_asset_impacts(raw_at_risk)

    raw_to_benefit = update.get("assets_to_benefit", {})
    if isinstance(raw_to_benefit, dict) and raw_to_benefit:
        narrative.assets_to_benefit = _parse_asset_impacts(raw_to_benefit)

    # Parse updated cascading effects
    raw_effects = update.get("cascading_effects", [])
    if isinstance(raw_effects, list) and raw_effects:
        cascading_effects: list[CascadingEffect] = []
        for eff in raw_effects:
            if isinstance(eff, dict) and "effect" in eff and "mechanism" in eff:
                old_subs = eff.get("affected_sub_assets", [])
                cascading_effects.append(
                    CascadingEffect(
                        order=int(eff.get("order", 2)),
                        direction=eff.get("direction", "negative"),
                        timeframe=eff.get("timeframe", ""),
                        effect=eff["effect"],
                        mechanism=eff["mechanism"],
                        sub_assets_at_risk=[
                            str(a) for a in
                            eff.get("sub_assets_at_risk", old_subs)
                        ],
                        sub_assets_to_benefit=[
                            str(a) for a in
                            eff.get("sub_assets_to_benefit", [])
                        ],
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
