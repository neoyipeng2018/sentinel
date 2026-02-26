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
    FIXED_INCOME = "fixed_income"
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


class Narrative(BaseModel):
    """A risk narrative synthesized from multiple signals."""

    id: str = Field(default_factory=lambda: "")
    title: str
    summary: str
    risk_level: RiskLevel
    affected_assets: list[AssetClass]
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
