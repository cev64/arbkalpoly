from dataclasses import dataclass

@dataclass(frozen=True)
class OrderBookLevel:
    price: float
    quantity: float

@dataclass(frozen=True)
class OrderBook:
    yes_asks: tuple[OrderBookLevel, ...] = ()
    no_asks: tuple[OrderBookLevel, ...] = ()
