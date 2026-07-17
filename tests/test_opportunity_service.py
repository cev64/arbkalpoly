from datetime import UTC, datetime

import pytest

from backend.matcher.market_matcher import MarketMatch
from backend.models.market import NormalizedMarket
from backend.models.order_book import OrderBook, OrderBookLevel
from backend.services.opportunity_service import OpportunityService


def market(exchange: str, market_id: str, yes_best_ask: float, no_best_ask: float) -> NormalizedMarket:
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
        updated_at=datetime.now(UTC),
    )


def order_books() -> tuple[OrderBook, OrderBook]:
    kalshi_book = OrderBook(yes_asks=(OrderBookLevel(0.47, 100),), no_asks=(OrderBookLevel(0.55, 100),))
    polymarket_book = OrderBook(yes_asks=(OrderBookLevel(0.46, 100),), no_asks=(OrderBookLevel(0.49, 100),))
    return kalshi_book, polymarket_book


def confirmed_match() -> MarketMatch:
    return MarketMatch(
        kalshi=market("kalshi", "k1", 0.47, 0.55),
        polymarket=market("polymarket", "p1", 0.46, 0.49),
        confidence=100,
        status="confirmed",
        explanation="No obvious settlement-rule mismatch detected.",
    )


def test_opportunity_is_confirmed_when_market_data_is_fresh():
    now = datetime.now(UTC)
    match = confirmed_match()
    kalshi_book, polymarket_book = order_books()

    opportunities = OpportunityService().from_match(match, kalshi_book, polymarket_book, now, False)

    assert len(opportunities) == 1
    assert opportunities[0].status == "confirmed"


def test_opportunity_reports_per_side_stake_and_fee_breakdown():
    now = datetime.now(UTC)
    match = confirmed_match()
    kalshi_book, polymarket_book = order_books()

    opportunity = OpportunityService().from_match(match, kalshi_book, polymarket_book, now, False)[0]

    assert opportunity.kalshi_side == "YES"
    assert opportunity.contracts == 100
    assert opportunity.kalshi_stake == 47.0
    assert opportunity.kalshi_fee == 1.75
    assert opportunity.polymarket_side == "NO"
    assert opportunity.polymarket_stake == 49.0
    assert opportunity.polymarket_fee == 0.0
    assert opportunity.kalshi_stake + opportunity.polymarket_stake == opportunity.gross_cost
    assert opportunity.kalshi_fee + opportunity.polymarket_fee == opportunity.estimated_fees


def test_opportunity_sizing_targets_configured_stake_when_depth_is_larger():
    now = datetime.now(UTC)
    match = confirmed_match()
    kalshi_book = OrderBook(yes_asks=(OrderBookLevel(0.47, 10_000),), no_asks=(OrderBookLevel(0.55, 10_000),))
    polymarket_book = OrderBook(yes_asks=(OrderBookLevel(0.46, 10_000),), no_asks=(OrderBookLevel(0.49, 10_000),))

    opportunity = OpportunityService(target_stake_dollars=100.0).from_match(
        match, kalshi_book, polymarket_book, now, False
    )[0]

    # Polymarket NO @ 0.49 is the pricier leg, so it's the one that lands on the
    # $100 target; Kalshi YES @ 0.47 (cheaper) costs less for the same contracts.
    assert opportunity.polymarket_stake == pytest.approx(100.0, abs=0.01)
    assert opportunity.kalshi_stake < opportunity.polymarket_stake
    assert opportunity.contracts < 1000  # nowhere near the 10,000-deep book
    # The full executable depth is still reported separately for reference.
    assert opportunity.maximum_executable_cost > opportunity.gross_cost
    assert opportunity.maximum_expected_profit > opportunity.net_edge


def test_opportunity_is_marked_stale_when_discovery_pipeline_is_stale():
    stale_time = datetime.now(UTC)
    match = confirmed_match()
    kalshi_book, polymarket_book = order_books()

    opportunities = OpportunityService().from_match(match, kalshi_book, polymarket_book, stale_time, True)

    assert len(opportunities) == 1
    assert opportunities[0].status == "stale"
    assert opportunities[0].last_updated == stale_time


def test_stale_status_overrides_manual_review():
    stale_time = datetime.now(UTC)
    match = MarketMatch(
        kalshi=market("kalshi", "k1", 0.47, 0.55),
        polymarket=market("polymarket", "p1", 0.46, 0.49),
        confidence=85,
        status="manual_review",
        explanation="Rule wording differs.",
    )
    kalshi_book, polymarket_book = order_books()

    opportunities = OpportunityService().from_match(match, kalshi_book, polymarket_book, stale_time, True)

    assert opportunities[0].status == "stale"
