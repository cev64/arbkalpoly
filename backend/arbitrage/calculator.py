from dataclasses import dataclass
from backend.arbitrage.fees import estimate_fee

@dataclass(frozen=True)
class ArbitrageResult:
    gross_cost: float
    guaranteed_payout: float
    estimated_fees: float
    net_profit: float
    roi: float
    profitable: bool

def calculate_binary_arbitrage(yes_exchange: str, yes_price: float, no_exchange: str, no_price: float, quantity: float = 1.0) -> ArbitrageResult:
    gross_cost = (yes_price + no_price) * quantity
    guaranteed_payout = quantity
    fees = estimate_fee(yes_exchange, yes_price, quantity) + estimate_fee(no_exchange, no_price, quantity)
    net_profit = guaranteed_payout - gross_cost - fees
    roi = net_profit / gross_cost if gross_cost else 0.0
    return ArbitrageResult(gross_cost, guaranteed_payout, fees, net_profit, roi, net_profit > 0)
