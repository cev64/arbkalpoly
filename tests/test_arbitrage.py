from backend.arbitrage.calculator import calculate_binary_arbitrage
from backend.arbitrage.liquidity import blended_cost
from backend.models.order_book import OrderBookLevel


def test_profitable_binary_arbitrage():
    result = calculate_binary_arbitrage("kalshi", 0.47, "polymarket", 0.49)
    assert result.profitable
    assert round(result.net_profit, 2) == 0.04


def test_negative_edge():
    assert not calculate_binary_arbitrage("kalshi", 0.52, "polymarket", 0.51).profitable


def test_blended_cost_walks_depth():
    cost, filled = blended_cost((OrderBookLevel(0.45, 5), OrderBookLevel(0.50, 5)), 8)
    assert filled == 8
    assert cost == 3.75
