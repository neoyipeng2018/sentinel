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
    PREDICTION_MARKET = "prediction_market"
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


class AssetImpact(BaseModel):
    """A specific sub-asset with an explanation of how it's affected."""

    asset: str  # e.g. "US Technology", "USD/JPY"
    explanation: str  # e.g. "Higher rates compress tech valuations"


class CascadingEffect(BaseModel):
    """A second or third order effect stemming from a risk narrative."""

    order: int  # 2 = second order, 3 = third order
    direction: str = "negative"  # "negative" = harmful, "positive" = beneficial
    timeframe: str = ""  # e.g. "days", "1-2 weeks", "3-6 months"
    effect: str  # what happens
    mechanism: str  # why / the causal link
    sub_assets_at_risk: list[str] = Field(default_factory=list)
    sub_assets_to_benefit: list[str] = Field(default_factory=list)


class CounterNarrative(BaseModel):
    """The strongest argument against a risk narrative."""

    counter_argument: str
    basis: str  # what evidence or logic supports this counter
    confidence: float  # 0-1, how strong this counter-argument is


class Signpost(BaseModel):
    """A forward-looking indicator that would aggravate or mitigate a risk."""

    type: str  # "aggravating" or "mitigating"
    factor: str  # what to watch for
    detail: str  # why it matters


class Narrative(BaseModel):
    """A risk narrative synthesized from multiple signals."""

    id: str = Field(default_factory=lambda: "")
    title: str
    summary: str
    risk_level: RiskLevel
    affected_assets: list[AssetClass]
    assets_at_risk: dict[AssetClass, list[AssetImpact]] = Field(default_factory=dict)
    assets_to_benefit: dict[AssetClass, list[AssetImpact]] = Field(default_factory=dict)
    cascading_effects: list[CascadingEffect] = Field(default_factory=list)
    counter_narrative: CounterNarrative | None = None
    signposts: list[Signpost] = Field(default_factory=list)
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
