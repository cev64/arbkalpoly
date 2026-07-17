from datetime import UTC, datetime
from backend.matcher.market_matcher import match_markets
from backend.models.market import NormalizedMarket


def market(
    exchange: str, market_id: str, rules: str = "full game including extra innings", line: float | None = None
) -> NormalizedMarket:
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
        line=line,
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


def test_rule_mismatch_is_logged(caplog):
    with caplog.at_level("INFO"):
        match_markets(market("kalshi", "k1", "regulation only"), market("polymarket", "p1"), threshold=80)

    assert any("Rule mismatch" in record.message for record in caplog.records)


def test_rejected_match_is_logged_at_debug(caplog):
    with caplog.at_level("DEBUG"):
        result = match_markets(market("kalshi", "k1"), market("polymarket", "p1"), threshold=101)

    assert result is None
    assert any("Rejected match" in record.message for record in caplog.records)


def test_lines_within_tolerance_still_match():
    match = match_markets(
        market("kalshi", "k1", line=-1.5),
        market("polymarket", "p1", line=-1.5000001),
    )
    assert match is not None
    assert match.confidence == 100


def test_materially_different_lines_do_not_match():
    match = match_markets(
        market("kalshi", "k1", line=-1.5),
        market("polymarket", "p1", line=-2.5),
        threshold=90,
    )
    assert match is None


def test_line_present_on_only_one_side_does_not_match():
    match = match_markets(
        market("kalshi", "k1", line=-1.5),
        market("polymarket", "p1", line=None),
        threshold=90,
    )
    assert match is None
