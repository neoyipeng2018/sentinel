"""Basic tests for data models."""

from models.schemas import AssetClass, Narrative, RiskLevel, Signal, SignalSource


def test_signal_creation():
    signal = Signal(
        source=SignalSource.NEWS,
        title="Test signal",
        content="Some content",
    )
    assert signal.source == SignalSource.NEWS
    assert signal.title == "Test signal"


def test_narrative_creation():
    narrative = Narrative(
        title="Test narrative",
        summary="A test risk narrative",
        risk_level=RiskLevel.HIGH,
        affected_assets=[AssetClass.EQUITIES, AssetClass.FX],
    )
    assert narrative.risk_level == RiskLevel.HIGH
    assert len(narrative.affected_assets) == 2
    assert narrative.trend == "stable"
    assert narrative.asset_detail == {}


def test_narrative_with_asset_detail():
    detail = {
        AssetClass.EQUITIES: ["Technology", "Financials"],
        AssetClass.FX: ["USD/JPY"],
    }
    narrative = Narrative(
        title="Carry trade unwinding",
        summary="Rising JPY pressuring leveraged positions",
        risk_level=RiskLevel.HIGH,
        affected_assets=[AssetClass.EQUITIES, AssetClass.FX],
        asset_detail=detail,
    )
    assert narrative.asset_detail[AssetClass.EQUITIES] == ["Technology", "Financials"]
    assert narrative.asset_detail[AssetClass.FX] == ["USD/JPY"]
    assert len(narrative.asset_detail) == 2
