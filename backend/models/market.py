from dataclasses import dataclass
from datetime import datetime
from typing import Any, Literal

MarketType = Literal["moneyline", "future", "player_prop", "unknown"]

@dataclass(frozen=True)
class NormalizedMarket:
    exchange: str
    market_id: str
    sport: str
    league: str
    event_id: str
    event_start: datetime
    home_team: str | None
    away_team: str | None
    player: str | None
    market_type: MarketType
    selection: str
    line: float | None
    period: str
    yes_best_ask: float | None
    yes_best_bid: float | None
    no_best_ask: float | None
    no_best_bid: float | None
    rules_text: str
    market_url: str
    updated_at: datetime
    raw: dict[str, Any] | None = None
