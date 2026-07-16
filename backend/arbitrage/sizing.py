from backend.arbitrage.calculator import calculate_binary_arbitrage
from backend.models.order_book import OrderBookLevel

def max_equal_quantity(yes_levels: tuple[OrderBookLevel, ...], no_levels: tuple[OrderBookLevel, ...]) -> float:
    return min(sum(level.quantity for level in yes_levels), sum(level.quantity for level in no_levels))
