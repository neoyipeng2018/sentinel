"""Basic tests for data models."""

from models.schemas import AssetClass, AssetImpact, Narrative, RiskLevel, Signal, SignalSource


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
    assert narrative.assets_at_risk == {}
    assert narrative.assets_to_benefit == {}


def test_narrative_with_asset_impacts():
    at_risk = {
        AssetClass.EQUITIES: [
            AssetImpact(asset="US Technology", explanation="Higher rates compress valuations"),
            AssetImpact(asset="Japan Financials", explanation="Yen strength hits exports"),
        ],
        AssetClass.FX: [
            AssetImpact(asset="USD/JPY", explanation="Carry trade unwind drives yen up"),
        ],
    }
    to_benefit = {
        AssetClass.COMMODITIES: [
            AssetImpact(asset="Gold", explanation="Safe-haven demand rises"),
        ],
    }
    narrative = Narrative(
        title="Carry trade unwinding",
        summary="Rising JPY pressuring leveraged positions",
        risk_level=RiskLevel.HIGH,
        affected_assets=[AssetClass.EQUITIES, AssetClass.FX, AssetClass.COMMODITIES],
        assets_at_risk=at_risk,
        assets_to_benefit=to_benefit,
    )
    assert len(narrative.assets_at_risk[AssetClass.EQUITIES]) == 2
    assert narrative.assets_at_risk[AssetClass.FX][0].asset == "USD/JPY"
    assert narrative.assets_to_benefit[AssetClass.COMMODITIES][0].asset == "Gold"
