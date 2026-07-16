from backend.models.order_book import OrderBookLevel

def blended_cost(levels: tuple[OrderBookLevel, ...], quantity: float) -> tuple[float, float]:
    remaining = quantity
    cost = 0.0
    filled = 0.0
    for level in sorted(levels, key=lambda item: item.price):
        take = min(remaining, level.quantity)
        cost += take * level.price
        filled += take
        remaining -= take
        if remaining <= 0:
            break
    return cost, filled
