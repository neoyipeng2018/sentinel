from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class RiskLevel(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class AssetClass(str, Enum):
    EQUITIES = "equities"
    CREDIT = "credit"
    RATES = "rates"
    PRIVATE_MARKETS = "private_markets"
    REAL_ESTATE = "real_estate"
    COMMODITIES = "commodities"
    FX = "fx"


class SignalSource(str, Enum):
    NEWS = "news"
    MARKET_DATA = "market_data"
    SOCIAL = "social"
    CUSTOM = "custom"


class Signal(BaseModel):
    """A raw signal from any data source."""

    id: str = Field(default_factory=lambda: "")
    source: SignalSource
    title: str
    content: str
    url: str = ""
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    metadata: dict = Field(default_factory=dict)


class CascadingEffect(BaseModel):
    """A second or third order effect stemming from a risk narrative."""

    order: int  # 2 = second order, 3 = third order
    effect: str  # what happens
    mechanism: str  # why / the causal link
    affected_sub_assets: list[str] = Field(default_factory=list)  # e.g. ["USD/BRL", "USD/ZAR"]


class CounterNarrative(BaseModel):
    """The strongest argument against a risk narrative."""

    counter_argument: str
    basis: str  # what evidence or logic supports this counter
    confidence: float  # 0-1, how strong this counter-argument is


class Narrative(BaseModel):
    """A risk narrative synthesized from multiple signals."""

    id: str = Field(default_factory=lambda: "")
    title: str
    summary: str
    risk_level: RiskLevel
    affected_assets: list[AssetClass]
    asset_detail: dict[AssetClass, list[str]] = Field(default_factory=dict)
    cascading_effects: list[CascadingEffect] = Field(default_factory=list)
    counter_narrative: CounterNarrative | None = None
    signals: list[Signal] = Field(default_factory=list)
    first_seen: datetime = Field(default_factory=datetime.utcnow)
    last_updated: datetime = Field(default_factory=datetime.utcnow)
    trend: str = "stable"  # intensifying, stable, fading
    confidence: float = 0.0  # 0-1


class RiskBriefing(BaseModel):
    """An AI-generated risk briefing."""

    generated_at: datetime = Field(default_factory=datetime.utcnow)
    summary: str
    top_narratives: list[Narrative]
    market_outlook: str
    key_risks: list[str]
