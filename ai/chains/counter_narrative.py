"""Generate counter-narratives (blindspots) for risk narratives using LLM."""

import json

from langchain_core.language_models import BaseChatModel

from ai.prompts.templates import COUNTER_NARRATIVE_PROMPT
from models.schemas import CounterNarrative, Narrative


def generate_counter_narratives(
    narratives: list[Narrative], llm: BaseChatModel
) -> None:
    """Generate a counter-narrative for each narrative and attach in-place.

    Batches all narratives into a single LLM call to minimize API usage.
    """
    if not narratives:
        return

    # Format narratives for the prompt
    narrative_text = "\n\n".join(
        f"[{i + 1}] {n.title}\nSummary: {n.summary}\n"
        f"Signals: {len(n.signals)} | Risk: {n.risk_level.value} | Trend: {n.trend}"
        for i, n in enumerate(narratives)
    )

    chain = COUNTER_NARRATIVE_PROMPT | llm
    response = chain.invoke({"narratives": narrative_text})

    try:
        raw = response.content
        # Handle markdown-wrapped JSON
        if "```" in raw:
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        parsed = json.loads(raw.strip())
    except (json.JSONDecodeError, IndexError):
        return

    if not isinstance(parsed, list):
        return

    # Match counter-narratives to narratives by position
    for i, item in enumerate(parsed):
        if i >= len(narratives):
            break
        try:
            narratives[i].counter_narrative = CounterNarrative(
                counter_argument=item["counter_argument"],
                basis=item["basis"],
                confidence=float(item.get("confidence", 0.5)),
            )
        except (KeyError, ValueError, TypeError):
            continue
