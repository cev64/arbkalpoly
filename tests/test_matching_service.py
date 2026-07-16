import asyncio
from dataclasses import replace
from datetime import UTC, datetime

from backend.models.market import NormalizedMarket
from backend.models.order_book import OrderBook, OrderBookLevel
from backend.services.market_cache import MarketCache
from backend.services.matching_service import MatchingService


def market(exchange: str, market_id: str, yes_best_ask: float, no_best_ask: float) -> NormalizedMarket:
    raw = None
    if exchange == "polymarket":
        raw = {"token_id": f"{market_id}-yes-token", "opposing_token_id": f"{market_id}-no-token"}
    return NormalizedMarket(
        exchange=exchange,
        market_id=market_id,
        sport="MLB",
        league="MLB",
        event_id="2026-07-16-NYM-ATL",
        event_start=datetime(2026, 7, 16, 23, 10, tzinfo=UTC),
        home_team="Atlanta Braves",
        away_team="New York Mets",
        player=None,
        market_type="moneyline",
        selection="New York Mets",
        line=None,
        period="full_game",
        yes_best_ask=yes_best_ask,
        yes_best_bid=yes_best_ask - 0.01,
        no_best_ask=no_best_ask,
        no_best_bid=no_best_ask - 0.01,
        rules_text="full game including extra innings",
        market_url="https://example.com",
        updated_at=datetime(2026, 7, 16, 22, 0, tzinfo=UTC),
        raw=raw,
    )


class FakeKalshiCollector:
    def __init__(self, books: dict[str, OrderBook]):
        self.books = books

    async def fetch_order_book(self, ticker: str) -> OrderBook:
        return self.books[ticker]


class FakePolymarketCollector:
    def __init__(self, books: dict[tuple[str, str], OrderBook]):
        self.books = books

    async def fetch_order_book(self, yes_token_id: str, no_token_id: str) -> OrderBook:
        return self.books[(yes_token_id, no_token_id)]


def test_find_matches_pairs_identical_markets_across_exchanges():
    cache = MarketCache()
    cache.upsert(market("kalshi", "k1", 0.47, 0.55))
    cache.upsert(market("polymarket", "p1", 0.46, 0.49))

    service = MatchingService(FakeKalshiCollector({}), FakePolymarketCollector({}), match_confidence_threshold=90)
    matches = service.find_matches(cache)

    assert len(matches) == 1
    assert matches[0].status == "confirmed"


def test_find_matches_ignores_different_leagues():
    cache = MarketCache()
    cache.upsert(market("kalshi", "k1", 0.47, 0.55))
    cache.upsert(replace(market("polymarket", "p1", 0.46, 0.49), league="NFL"))

    service = MatchingService(FakeKalshiCollector({}), FakePolymarketCollector({}), match_confidence_threshold=90)

    assert service.find_matches(cache) == []


def test_find_opportunities_flags_profitable_cross_exchange_arbitrage():
    cache = MarketCache()
    cache.upsert(market("kalshi", "k1", 0.47, 0.55))
    cache.upsert(market("polymarket", "p1", 0.46, 0.49))

    kalshi_collector = FakeKalshiCollector({
        "k1": OrderBook(yes_asks=(OrderBookLevel(0.47, 100),), no_asks=(OrderBookLevel(0.55, 100),)),
    })
    polymarket_collector = FakePolymarketCollector({
        ("p1-yes-token", "p1-no-token"): OrderBook(
            yes_asks=(OrderBookLevel(0.46, 100),), no_asks=(OrderBookLevel(0.49, 100),)
        ),
    })
    service = MatchingService(kalshi_collector, polymarket_collector, match_confidence_threshold=90)

    opportunities = asyncio.run(service.find_opportunities(cache))

    assert len(opportunities) == 1
    assert opportunities[0].kalshi_side == "YES"
    assert opportunities[0].polymarket_side == "NO"
    assert opportunities[0].net_edge > 0


def test_find_opportunities_skips_matches_with_no_edge():
    cache = MarketCache()
    cache.upsert(market("kalshi", "k1", 0.52, 0.55))
    cache.upsert(market("polymarket", "p1", 0.51, 0.54))

    kalshi_collector = FakeKalshiCollector({
        "k1": OrderBook(yes_asks=(OrderBookLevel(0.52, 100),), no_asks=(OrderBookLevel(0.55, 100),)),
    })
    polymarket_collector = FakePolymarketCollector({
        ("p1-yes-token", "p1-no-token"): OrderBook(
            yes_asks=(OrderBookLevel(0.51, 100),), no_asks=(OrderBookLevel(0.54, 100),)
        ),
    })
    service = MatchingService(kalshi_collector, polymarket_collector, match_confidence_threshold=90)

    assert asyncio.run(service.find_opportunities(cache)) == []


def test_find_opportunities_skips_matches_missing_token_metadata():
    cache = MarketCache()
    cache.upsert(market("kalshi", "k1", 0.47, 0.55))
    cache.upsert(replace(market("polymarket", "p1", 0.46, 0.49), raw=None))

    service = MatchingService(FakeKalshiCollector({}), FakePolymarketCollector({}), match_confidence_threshold=90)

    assert asyncio.run(service.find_opportunities(cache)) == []
