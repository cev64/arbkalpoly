from dataclasses import dataclass

from backend.arbitrage.fees import estimate_fee
from backend.models.order_book import OrderBookLevel


@dataclass(frozen=True)
class DepthSizingResult:
    quantity: float
    yes_cost: float
    no_cost: float
    yes_fee: float
    no_fee: float
    gross_cost: float
    estimated_fees: float
    net_profit: float
    roi: float


def size_binary_arbitrage(
    yes_exchange: str,
    yes_asks: tuple[OrderBookLevel, ...],
    no_exchange: str,
    no_asks: tuple[OrderBookLevel, ...],
    max_quantity: float | None = None,
) -> DepthSizingResult:
    """Walk both ask books together, taking every unit whose combined price is still below 1.

    Fees are applied per level after sizing rather than as a stopping condition, so the
    reported quantity can include a marginal level that only turns unprofitable once fees
    are subtracted; callers should reject the final result unless net_profit stays positive.

    Pass max_quantity to cap the walk at a practical position size instead of the full
    executable depth (e.g. sizing a $100-equivalent position rather than every contract
    the book could theoretically fill).
    """
    yes_levels = sorted(yes_asks, key=lambda level: level.price)
    no_levels = sorted(no_asks, key=lambda level: level.price)

    quantity = 0.0
    yes_cost = 0.0
    no_cost = 0.0
    yes_fee = 0.0
    no_fee = 0.0
    yes_index = no_index = 0
    yes_remaining = yes_levels[0].quantity if yes_levels else 0.0
    no_remaining = no_levels[0].quantity if no_levels else 0.0

    while yes_index < len(yes_levels) and no_index < len(no_levels):
        yes_level = yes_levels[yes_index]
        no_level = no_levels[no_index]
        if yes_level.price + no_level.price >= 1:
            break

        take = min(yes_remaining, no_remaining)
        if max_quantity is not None:
            take = min(take, max_quantity - quantity)
        if take <= 0:
            break

        yes_cost += take * yes_level.price
        no_cost += take * no_level.price
        yes_fee += estimate_fee(yes_exchange, yes_level.price, take)
        no_fee += estimate_fee(no_exchange, no_level.price, take)
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

    gross_cost = yes_cost + no_cost
    estimated_fees = yes_fee + no_fee
    net_profit = quantity - gross_cost - estimated_fees
    roi = net_profit / gross_cost if gross_cost else 0.0
    return DepthSizingResult(quantity, yes_cost, no_cost, yes_fee, no_fee, gross_cost, estimated_fees, net_profit, roi)
