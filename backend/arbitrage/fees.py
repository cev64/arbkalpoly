"""Exchange trading-fee schedules.

Kalshi (general fee schedule, effective 2024, applies to both sides on most
markets): fee = ceil(0.07 * price * (1 - price) * quantity * 100) / 100
dollars. Source: https://kalshi.com/docs/kalshi-fee-schedule

Polymarket (as of this writing): the CLOB charges no protocol trading fee;
the on-chain fee switch exists but is set to 0%.
Source: https://docs.polymarket.com/#fees
"""
import math
from dataclasses import dataclass


@dataclass(frozen=True)
class FeeConfig:
    kalshi_rate: float = 0.07
    polymarket_rate: float = 0.0


DEFAULT_FEE_CONFIG = FeeConfig()


def _kalshi_fee(price: float, quantity: float, rate: float) -> float:
    if quantity <= 0 or price <= 0 or price >= 1:
        return 0.0
    raw = rate * price * (1 - price) * quantity
    return math.ceil(raw * 100) / 100


def _polymarket_fee(price: float, quantity: float, rate: float) -> float:
    return price * quantity * rate


def estimate_fee(exchange: str, price: float, quantity: float, config: FeeConfig = DEFAULT_FEE_CONFIG) -> float:
    exchange = exchange.lower()
    if exchange == "kalshi":
        return _kalshi_fee(price, quantity, config.kalshi_rate)
    if exchange == "polymarket":
        return _polymarket_fee(price, quantity, config.polymarket_rate)
    raise ValueError(f"Unknown exchange: {exchange}")
