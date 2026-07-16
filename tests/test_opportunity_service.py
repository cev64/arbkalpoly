from datetime import UTC, datetime, timedelta

from backend.matcher.market_matcher import MarketMatch
from backend.models.market import NormalizedMarket
from backend.models.order_book import OrderBook, OrderBookLevel
from backend.services.opportunity_service import OpportunityService


def market(exchange: str, market_id: str, yes_best_ask: float, no_best_ask: float, updated_at: datetime) -> NormalizedMarket:
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
        updated_at=updated_at,
    )


def order_books() -> tuple[OrderBook, OrderBook]:
    kalshi_book = OrderBook(yes_asks=(OrderBookLevel(0.47, 100),), no_asks=(OrderBookLevel(0.55, 100),))
    polymarket_book = OrderBook(yes_asks=(OrderBookLevel(0.46, 100),), no_asks=(OrderBookLevel(0.49, 100),))
    return kalshi_book, polymarket_book


def test_opportunity_is_confirmed_when_market_data_is_fresh():
    now = datetime.now(UTC)
    match = MarketMatch(
        kalshi=market("kalshi", "k1", 0.47, 0.55, now),
        polymarket=market("polymarket", "p1", 0.46, 0.49, now),
        confidence=100,
        status="confirmed",
        explanation="No obvious settlement-rule mismatch detected.",
    )
    kalshi_book, polymarket_book = order_books()

    opportunities = OpportunityService(stale_after_seconds=15).from_match(match, kalshi_book, polymarket_book)

    assert len(opportunities) == 1
    assert opportunities[0].status == "confirmed"


def test_opportunity_is_marked_stale_when_either_market_is_old():
    now = datetime.now(UTC)
    stale_time = now - timedelta(seconds=60)
    match = MarketMatch(
        kalshi=market("kalshi", "k1", 0.47, 0.55, stale_time),
        polymarket=market("polymarket", "p1", 0.46, 0.49, now),
        confidence=100,
        status="confirmed",
        explanation="No obvious settlement-rule mismatch detected.",
    )
    kalshi_book, polymarket_book = order_books()

    opportunities = OpportunityService(stale_after_seconds=15).from_match(match, kalshi_book, polymarket_book)

    assert len(opportunities) == 1
    assert opportunities[0].status == "stale"
    assert opportunities[0].last_updated == stale_time


def test_stale_status_overrides_manual_review():
    stale_time = datetime.now(UTC) - timedelta(seconds=60)
    match = MarketMatch(
        kalshi=market("kalshi", "k1", 0.47, 0.55, stale_time),
        polymarket=market("polymarket", "p1", 0.46, 0.49, stale_time),
        confidence=85,
        status="manual_review",
        explanation="Rule wording differs.",
    )
    kalshi_book, polymarket_book = order_books()

    opportunities = OpportunityService(stale_after_seconds=15).from_match(match, kalshi_book, polymarket_book)

    assert opportunities[0].status == "stale"
