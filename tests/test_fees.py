import pytest

from backend.arbitrage.fees import FeeConfig, estimate_fee


def test_kalshi_fee_matches_published_formula():
    assert estimate_fee("kalshi", 0.47, 1) == 0.02


def test_polymarket_fee_is_zero_by_default():
    assert estimate_fee("polymarket", 0.47, 100) == 0.0


def test_fee_config_is_overridable():
    config = FeeConfig(kalshi_rate=0.0, polymarket_rate=0.01)
    assert estimate_fee("kalshi", 0.47, 1, config=config) == 0.0
    assert round(estimate_fee("polymarket", 0.5, 100, config=config), 2) == 0.5


def test_unknown_exchange_raises_and_logs_error(caplog):
    with caplog.at_level("ERROR"), pytest.raises(ValueError):
        estimate_fee("bogus", 0.5, 1)

    assert any("Fee calculation error" in record.message for record in caplog.records)
