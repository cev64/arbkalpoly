from datetime import UTC, datetime
from backend.matcher.market_matcher import match_markets
from backend.models.market import NormalizedMarket


def market(exchange: str, market_id: str, rules: str = "full game including extra innings") -> NormalizedMarket:
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
        yes_best_ask=0.47,
        yes_best_bid=0.46,
        no_best_ask=0.55,
        no_best_bid=0.53,
        rules_text=rules,
        market_url="https://example.com",
        updated_at=datetime(2026, 7, 16, 22, 0, tzinfo=UTC),
    )


def test_identical_markets_match():
    match = match_markets(market("kalshi", "k1"), market("polymarket", "p1"))
    assert match is not None
    assert match.confidence == 100
    assert match.status == "confirmed"


def test_rule_difference_requires_manual_review():
    match = match_markets(market("kalshi", "k1", "regulation only"), market("polymarket", "p1"), threshold=80)
    assert match is not None
    assert match.status == "manual_review"
