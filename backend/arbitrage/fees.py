from dataclasses import dataclass

@dataclass(frozen=True)
class FeeConfig:
    kalshi_rate: float = 0.0
    polymarket_rate: float = 0.0

DEFAULT_FEE_CONFIG = FeeConfig()

def estimate_fee(exchange: str, price: float, quantity: float, config: FeeConfig = DEFAULT_FEE_CONFIG) -> float:
    rate = config.kalshi_rate if exchange.lower() == "kalshi" else config.polymarket_rate
    return price * quantity * rate
