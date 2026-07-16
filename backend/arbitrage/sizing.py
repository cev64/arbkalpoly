from dataclasses import dataclass

from backend.arbitrage.fees import estimate_fee
from backend.models.order_book import OrderBookLevel


@dataclass(frozen=True)
class DepthSizingResult:
    quantity: float
    gross_cost: float
    estimated_fees: float
    net_profit: float
    roi: float


def size_binary_arbitrage(
    yes_exchange: str,
    yes_asks: tuple[OrderBookLevel, ...],
    no_exchange: str,
    no_asks: tuple[OrderBookLevel, ...],
) -> DepthSizingResult:
    """Walk both ask books together, taking every unit whose combined price is still below 1.

    Fees are applied per level after sizing rather than as a stopping condition, so the
    reported quantity can include a marginal level that only turns unprofitable once fees
    are subtracted; callers should reject the final result unless net_profit stays positive.
    """
    yes_levels = sorted(yes_asks, key=lambda level: level.price)
    no_levels = sorted(no_asks, key=lambda level: level.price)

    quantity = 0.0
    gross_cost = 0.0
    fees = 0.0
    yes_index = no_index = 0
    yes_remaining = yes_levels[0].quantity if yes_levels else 0.0
    no_remaining = no_levels[0].quantity if no_levels else 0.0

    while yes_index < len(yes_levels) and no_index < len(no_levels):
        yes_level = yes_levels[yes_index]
        no_level = no_levels[no_index]
        if yes_level.price + no_level.price >= 1:
            break

        take = min(yes_remaining, no_remaining)
        if take <= 0:
            break

        gross_cost += take * (yes_level.price + no_level.price)
        fees += estimate_fee(yes_exchange, yes_level.price, take) + estimate_fee(no_exchange, no_level.price, take)
        quantity += take

        yes_remaining -= take
        no_remaining -= take
        if yes_remaining <= 0:
            yes_index += 1
            if yes_index < len(yes_levels):
                yes_remaining = yes_levels[yes_index].quantity
        if no_remaining <= 0:
            no_index += 1
            if no_index < len(no_levels):
                no_remaining = no_levels[no_index].quantity

    net_profit = quantity - gross_cost - fees
    roi = net_profit / gross_cost if gross_cost else 0.0
    return DepthSizingResult(quantity, gross_cost, fees, net_profit, roi)
