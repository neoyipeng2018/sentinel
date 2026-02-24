"""Extract risk narratives from raw signals using LLM."""

import json
import uuid
from datetime import datetime

from langchain_core.language_models import BaseChatModel

from ai.prompts.templates import NARRATIVE_EXTRACTION_PROMPT
from models.schemas import AssetClass, Narrative, RiskLevel, Signal


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
            narrative = Narrative(
                id=uuid.uuid4().hex[:12],
                title=item["title"],
                summary=item["summary"],
                risk_level=RiskLevel(item["risk_level"]),
                affected_assets=[AssetClass(a) for a in item.get("affected_assets", [])],
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
