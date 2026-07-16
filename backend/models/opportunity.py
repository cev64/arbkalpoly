from dataclasses import dataclass
from datetime import datetime
from typing import Literal

OpportunityStatus = Literal["confirmed", "manual_review", "stale", "insufficient_liquidity", "no_longer_profitable", "rules_mismatch"]

@dataclass(frozen=True)
class Opportunity:
    id: str
    sport: str
    event: str
    market: str
    event_start: datetime
    kalshi_side: str
    kalshi_price: float
    polymarket_side: str
    polymarket_price: float
    gross_cost: float
    estimated_fees: float
    net_edge: float
    roi: float
    maximum_executable_cost: float
    maximum_expected_profit: float
    match_confidence: int
    status: OpportunityStatus
    last_updated: datetime
    kalshi_url: str
    polymarket_url: str
