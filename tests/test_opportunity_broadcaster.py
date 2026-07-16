import asyncio

from backend.models.order_book import OrderBook, OrderBookLevel
from backend.services.matching_service import MatchingService
from backend.services.market_cache import MarketCache
from backend.services.opportunity_broadcaster import OpportunityBroadcaster
from tests.test_matching_service import FakeKalshiCollector, FakePolymarketCollector, market


class CountingKalshiCollector(FakeKalshiCollector):
    def __init__(self, books):
        super().__init__(books)
        self.call_count = 0

    async def fetch_order_book(self, ticker: str) -> OrderBook:
        self.call_count += 1
        return await super().fetch_order_book(ticker)


def test_refresh_once_computes_a_single_snapshot_for_every_subscriber():
    cache = MarketCache()
    cache.upsert(market("kalshi", "k1", 0.47, 0.55))
    cache.upsert(market("polymarket", "p1", 0.46, 0.49))

    kalshi_collector = CountingKalshiCollector({
        "k1": OrderBook(yes_asks=(OrderBookLevel(0.47, 100),), no_asks=(OrderBookLevel(0.55, 100),)),
    })
    polymarket_collector = FakePolymarketCollector({
        ("p1-yes-token", "p1-no-token"): OrderBook(
            yes_asks=(OrderBookLevel(0.46, 100),), no_asks=(OrderBookLevel(0.49, 100),)
        ),
    })
    matching_service = MatchingService(kalshi_collector, polymarket_collector, match_confidence_threshold=90)
    broadcaster = OpportunityBroadcaster(cache, matching_service, interval_seconds=60)

    queue_a = broadcaster.subscribe()
    queue_b = broadcaster.subscribe()

    asyncio.run(broadcaster.refresh_once())

    result_a = queue_a.get_nowait()
    result_b = queue_b.get_nowait()

    assert result_a is result_b
    assert len(result_a) == 1
    assert kalshi_collector.call_count == 1


def test_unsubscribe_stops_further_pushes():
    cache = MarketCache()
    matching_service = MatchingService(FakeKalshiCollector({}), FakePolymarketCollector({}), match_confidence_threshold=90)
    broadcaster = OpportunityBroadcaster(cache, matching_service, interval_seconds=60)

    queue = broadcaster.subscribe()
    broadcaster.unsubscribe(queue)
    queue.get_nowait()  # drain the initial seed value

    asyncio.run(broadcaster.refresh_once())

    assert queue.empty()
