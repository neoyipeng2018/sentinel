"""Generate risk signposts (aggravating/mitigating factors) for narratives using LLM."""

import json
from datetime import date

from langchain_core.language_models import BaseChatModel

from ai.prompts.templates import SIGNPOST_PROMPT
from models.schemas import Narrative, Signpost


def generate_signposts(
    narratives: list[Narrative], llm: BaseChatModel
) -> None:
    """Generate signposts for each narrative and attach in-place.

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

    chain = SIGNPOST_PROMPT | llm
    response = chain.invoke({
        "narratives": narrative_text,
        "today": date.today().isoformat(),
    })

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

    # Match signposts to narratives by position
    for i, item in enumerate(parsed):
        if i >= len(narratives):
            break
        try:
            signposts_raw = item.get("signposts", [])
            narratives[i].signposts = [
                Signpost(
                    type=sp["type"],
                    factor=sp["factor"],
                    detail=sp["detail"],
                )
                for sp in signposts_raw
                if isinstance(sp, dict)
                and sp.get("type") in ("aggravating", "mitigating")
            ]
        except (KeyError, ValueError, TypeError):
            continue
