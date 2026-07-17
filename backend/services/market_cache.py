from dataclasses import asdict
from datetime import UTC, datetime

from backend.models.market import NormalizedMarket

class MarketCache:
    def __init__(self) -> None:
        self._markets: dict[str, NormalizedMarket] = {}
        self._last_refreshed: dict[str, datetime] = {}

    def upsert(self, market: NormalizedMarket) -> None:
        self._markets[f"{market.exchange}:{market.market_id}"] = market

    def replace_exchange(self, exchange: str, markets: list[NormalizedMarket]) -> None:
        prefix = f"{exchange.lower()}:"
        self._markets = {
            key: market for key, market in self._markets.items()
            if not key.lower().startswith(prefix)
        }
        for market in markets:
            self.upsert(market)
        self._last_refreshed[exchange.lower()] = datetime.now(UTC)

    def last_refreshed(self, exchange: str) -> datetime | None:
        """When discovery last successfully refreshed this exchange's market list.

        Individual exchanges' own per-market "updated" timestamps reflect when that
        market's price last changed there, not when we last fetched it - for an
        illiquid market that can be hours or days old even though we just confirmed
        its current state seconds ago. This is the actual freshness signal to use
        for staleness: is our own discovery pipeline still successfully refreshing.
        """
        return self._last_refreshed.get(exchange.lower())

    def set_last_refreshed(self, exchange: str, when: datetime) -> None:
        """Test-seeding hook for simulating discovery staleness without a real refresh."""
        self._last_refreshed[exchange.lower()] = when

    def all(
        self,
        exchange: str | None = None,
        sport: str | None = None,
        league: str | None = None,
    ) -> list[NormalizedMarket]:
        markets = self._markets.values()
        if exchange:
            markets = (market for market in markets if market.exchange.lower() == exchange.lower())
        if sport:
            markets = (market for market in markets if market.sport.lower() == sport.lower())
        if league:
            markets = (market for market in markets if market.league.lower() == league.lower())
        return sorted(markets, key=lambda market: (market.event_start, market.exchange, market.market_id))

    def count(self) -> int:
        return len(self._markets)

    @staticmethod
    def serialize(market: NormalizedMarket, include_raw: bool = False) -> dict:
        data = asdict(market)
        data["event_start"] = market.event_start.isoformat()
        data["updated_at"] = market.updated_at.isoformat()
        if not include_raw:
            data.pop("raw", None)
        return data
