"""Extract risk narratives from raw signals using LLM."""

import json
import uuid
from datetime import datetime

from langchain_core.language_models import BaseChatModel

from ai.prompts.templates import NARRATIVE_EXTRACTION_PROMPT
from models.schemas import AssetClass, AssetImpact, CascadingEffect, Narrative, RiskLevel, Signal


def _parse_asset_impacts(raw: dict) -> dict[AssetClass, list[AssetImpact]]:
    """Parse an assets_at_risk or assets_to_benefit dict from LLM JSON."""
    result: dict[AssetClass, list[AssetImpact]] = {}
    if not isinstance(raw, dict):
        return result
    for key, items in raw.items():
        try:
            ac = AssetClass(key)
        except ValueError:
            continue
        if isinstance(items, list):
            impacts = []
            for item in items:
                if isinstance(item, dict) and "asset" in item:
                    impacts.append(
                        AssetImpact(
                            asset=str(item["asset"]),
                            explanation=str(item.get("explanation", "")),
                        )
                    )
                elif isinstance(item, str):
                    # Backward compat: plain string list
                    impacts.append(AssetImpact(asset=item, explanation=""))
            if impacts:
                result[ac] = impacts
    return result


def extract_narratives(signals: list[Signal], llm: BaseChatModel) -> list[Narrative]:
    """Process a batch of signals and extract coherent risk narratives."""
    if not signals:
        return []

    # Format signals for the prompt
    signal_text = "\n\n".join(
        f"[{s.id}] ({s.source.value}) {s.title}\n{s.content[:300]}" for s in signals
    )

    chain = NARRATIVE_EXTRACTION_PROMPT | llm
    response = chain.invoke({"signals": signal_text})

    # Build a lookup for signals by ID
    signal_map = {s.id: s for s in signals}

    try:
        raw = response.content
        # Handle markdown-wrapped JSON
        if "```" in raw:
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        parsed = json.loads(raw.strip())
    except (json.JSONDecodeError, IndexError):
        return []

    narratives: list[Narrative] = []
    for item in parsed:
        try:
            matched_signals = [
                signal_map[sid]
                for sid in item.get("signal_ids", [])
                if sid in signal_map
            ]
            # Parse assets_at_risk and assets_to_benefit
            assets_at_risk = _parse_asset_impacts(item.get("assets_at_risk", {}))
            assets_to_benefit = _parse_asset_impacts(item.get("assets_to_benefit", {}))

            # Parse cascading effects
            raw_effects = item.get("cascading_effects", [])
            cascading_effects: list[CascadingEffect] = []
            for eff in raw_effects:
                if isinstance(eff, dict) and "effect" in eff and "mechanism" in eff:
                    cascading_effects.append(
                        CascadingEffect(
                            order=int(eff.get("order", 2)),
                            direction=eff.get("direction", "negative"),
                            effect=eff["effect"],
                            mechanism=eff["mechanism"],
                            affected_sub_assets=[
                                str(a) for a in eff.get("affected_sub_assets", [])
                            ],
                        )
                    )

            narrative = Narrative(
                id=uuid.uuid4().hex[:12],
                title=item["title"],
                summary=item["summary"],
                risk_level=RiskLevel(item["risk_level"]),
                affected_assets=[AssetClass(a) for a in item.get("affected_assets", [])],
                assets_at_risk=assets_at_risk,
                assets_to_benefit=assets_to_benefit,
                cascading_effects=cascading_effects,
                signals=matched_signals,
                first_seen=datetime.utcnow(),
                last_updated=datetime.utcnow(),
                trend=item.get("trend", "stable"),
                confidence=item.get("confidence", 0.5),
            )
            narratives.append(narrative)
        except (KeyError, ValueError) as e:
            print(f"Error parsing narrative: {e}")
            continue

    return narratives
