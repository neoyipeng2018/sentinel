"""Generate AI risk briefings from active narratives."""

from datetime import datetime

from langchain_core.language_models import BaseChatModel

from ai.chains.risk_assessor import get_top_risks
from ai.prompts.templates import RISK_BRIEFING_PROMPT
from models.schemas import Narrative, RiskBriefing


def generate_briefing(narratives: list[Narrative], llm: BaseChatModel) -> RiskBriefing:
    """Generate a comprehensive risk briefing from active narratives."""
    top = get_top_risks(narratives, n=10)

    def _format_assets(n: Narrative) -> str:
        risk_parts = []
        for a, imps in n.assets_at_risk.items():
            subs = ", ".join(i.asset for i in imps)
            risk_parts.append(f"{a.value} ({subs})")
        benefit_parts = []
        for a, imps in n.assets_to_benefit.items():
            subs = ", ".join(i.asset for i in imps)
            benefit_parts.append(f"{a.value} ({subs})")
        result = ""
        if risk_parts:
            result += "At risk: " + ", ".join(risk_parts)
        if benefit_parts:
            if result:
                result += " | "
            result += "Benefit: " + ", ".join(benefit_parts)
        return result or ", ".join(a.value for a in n.affected_assets)

    narrative_text = "\n\n".join(
        f"**{n.title}** (Risk: {n.risk_level.value}, Trend: {n.trend})\n"
        f"Assets: {_format_assets(n)}\n"
        f"Summary: {n.summary}\n"
        f"Signals: {len(n.signals)} | Confidence: {n.confidence:.0%}"
        for n in top
    )

    chain = RISK_BRIEFING_PROMPT | llm
    response = chain.invoke({"narratives": narrative_text})

    # Parse the key risks from the briefing
    briefing_text = response.content
    key_risks = [n.title for n in top[:5]]

    # Extract market outlook section if present
    market_outlook = ""
    if "Market Outlook" in briefing_text:
        parts = briefing_text.split("Market Outlook")
        if len(parts) > 1:
            outlook_section = parts[1]
            # Take until next section header
            for header in ["Watchlist", "##", "**"]:
                if header in outlook_section[10:]:
                    outlook_section = outlook_section[: outlook_section.index(header, 10)]
                    break
            market_outlook = outlook_section.strip().lstrip("*#: \n")

    return RiskBriefing(
        generated_at=datetime.utcnow(),
        summary=briefing_text,
        top_narratives=top[:5],
        market_outlook=market_outlook or "See briefing for details.",
        key_risks=key_risks,
    )
