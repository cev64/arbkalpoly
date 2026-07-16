import asyncio
from datetime import UTC, datetime

from backend.models.market import NormalizedMarket
from backend.services.market_cache import MarketCache
from backend.services.market_discovery import MarketDiscoveryService


def market(exchange: str, market_id: str) -> NormalizedMarket:
    now = datetime(2026, 7, 17, tzinfo=UTC)
    return NormalizedMarket(
        exchange=exchange,
        market_id=market_id,
        sport="MLB",
        league="MLB",
        event_id="game-1",
        event_start=now,
        home_team="Boston Red Sox",
        away_team="Tampa Bay Rays",
        player=None,
        market_type="moneyline",
        selection="Tampa Bay Rays",
        line=None,
        period="full_game",
        yes_best_ask=0.46,
        yes_best_bid=0.45,
        no_best_ask=0.55,
        no_best_bid=0.54,
        rules_text="full game",
        market_url="https://example.com",
        updated_at=now,
    )


class Collector:
    def __init__(self, exchange: str, result=None, error: Exception | None = None):
        self.exchange = exchange
        self.result = result or []
        self.error = error

    async def fetch_markets(self):
        if self.error:
            raise self.error
        return self.result


def test_refresh_keeps_successful_exchange_when_other_fails():
    cache = MarketCache()
    service = MarketDiscoveryService(cache, [
        Collector("kalshi", [market("kalshi", "k1")]),
        Collector("polymarket", error=RuntimeError("feed unavailable")),
    ])

    refreshed = asyncio.run(service.refresh())

    assert refreshed == 1
    assert cache.count() == 1
    assert "polymarket" in service.errors
    assert service.last_success is not None


def test_replace_exchange_removes_old_snapshot_only_for_that_exchange():
    cache = MarketCache()
    cache.upsert(market("kalshi", "old"))
    cache.upsert(market("polymarket", "p1"))

    cache.replace_exchange("kalshi", [market("kalshi", "new")])

    assert [item.market_id for item in cache.all(exchange="kalshi")] == ["new"]
    assert [item.market_id for item in cache.all(exchange="polymarket")] == ["p1"]
