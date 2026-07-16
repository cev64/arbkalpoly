from backend.models.market import NormalizedMarket

class MarketCache:
    def __init__(self) -> None:
        self._markets: dict[str, NormalizedMarket] = {}

    def upsert(self, market: NormalizedMarket) -> None:
        self._markets[f"{market.exchange}:{market.market_id}"] = market

    def all(self) -> list[NormalizedMarket]:
        return list(self._markets.values())
