from dataclasses import asdict

from backend.models.market import NormalizedMarket

class MarketCache:
    def __init__(self) -> None:
        self._markets: dict[str, NormalizedMarket] = {}

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
