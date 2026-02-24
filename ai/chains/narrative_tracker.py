"""Track and update existing narratives with new signals."""

import json
from datetime import datetime

from langchain_core.language_models import BaseChatModel

from ai.prompts.templates import NARRATIVE_UPDATE_PROMPT
from models.schemas import Narrative, RiskLevel, Signal


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
    narrative.signals.extend(new_signals)
    narrative.last_updated = datetime.utcnow()

    return narrative
