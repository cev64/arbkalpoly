from backend.arbitrage.calculator import calculate_binary_arbitrage
from backend.arbitrage.liquidity import blended_cost
from backend.arbitrage.sizing import size_binary_arbitrage
from backend.models.order_book import OrderBookLevel


def test_profitable_binary_arbitrage():
    result = calculate_binary_arbitrage("kalshi", 0.47, "polymarket", 0.49)
    assert result.profitable
    assert round(result.net_profit, 2) == 0.02


def test_negative_edge():
    assert not calculate_binary_arbitrage("kalshi", 0.52, "polymarket", 0.51).profitable


def test_blended_cost_walks_depth():
    cost, filled = blended_cost((OrderBookLevel(0.45, 5), OrderBookLevel(0.50, 5)), 8)
    assert filled == 8
    assert cost == 3.75


def test_size_binary_arbitrage_walks_matching_levels_until_unprofitable():
    yes_asks = (OrderBookLevel(0.40, 5), OrderBookLevel(0.50, 10))
    no_asks = (OrderBookLevel(0.45, 8), OrderBookLevel(0.60, 10))

    result = size_binary_arbitrage("kalshi", yes_asks, "polymarket", no_asks)

    assert result.quantity == 8
    assert round(result.gross_cost, 2) == 7.10
    assert round(result.net_profit, 2) == 0.75
    assert round(result.yes_cost, 2) == 3.50
    assert round(result.no_cost, 2) == 3.60
    assert round(result.yes_cost + result.no_cost, 2) == round(result.gross_cost, 2)


def test_size_binary_arbitrage_returns_zero_when_no_levels_are_profitable():
    yes_asks = (OrderBookLevel(0.60, 5),)
    no_asks = (OrderBookLevel(0.55, 5),)

    result = size_binary_arbitrage("kalshi", yes_asks, "polymarket", no_asks)

    assert result.quantity == 0
    assert result.gross_cost == 0
    assert result.net_profit == 0
