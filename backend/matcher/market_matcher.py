import logging
from dataclasses import dataclass
from backend.matcher.rule_validator import validate_rules
from backend.models.market import NormalizedMarket

logger = logging.getLogger(__name__)

LINE_TOLERANCE = 0.01

@dataclass(frozen=True)
class MarketMatch:
    kalshi: NormalizedMarket
    polymarket: NormalizedMarket
    confidence: int
    status: str
    explanation: str

def _lines_match(kalshi_line: float | None, polymarket_line: float | None) -> bool:
    """Compare betting lines with float tolerance instead of exact equality.

    Both sides are currently always None for moneyline markets, but a strict `==`
    would silently reject a real match the moment spreads/totals are added, since
    two exchanges' -1.5 can arrive as -1.5 and -1.4999999999 after parsing.
    """
    if kalshi_line is None or polymarket_line is None:
        return kalshi_line is polymarket_line
    return abs(kalshi_line - polymarket_line) <= LINE_TOLERANCE

def match_markets(kalshi: NormalizedMarket, polymarket: NormalizedMarket, threshold: int = 90) -> MarketMatch | None:
    score = 100
    checks = [
        kalshi.league == polymarket.league,
        kalshi.home_team == polymarket.home_team,
        kalshi.away_team == polymarket.away_team,
        kalshi.event_start.date() == polymarket.event_start.date(),
        kalshi.market_type == polymarket.market_type,
        kalshi.selection == polymarket.selection,
        _lines_match(kalshi.line, polymarket.line),
        kalshi.period == polymarket.period,
    ]
    score -= checks.count(False) * 15
    rules_ok, explanation = validate_rules(kalshi.rules_text, polymarket.rules_text)
    if not rules_ok:
        logger.info("Rule mismatch for %s/%s: %s", kalshi.market_id, polymarket.market_id, explanation)
        score -= 20
    if score < threshold:
        logger.debug(
            "Rejected match %s/%s: score=%d below threshold=%d", kalshi.market_id, polymarket.market_id, score, threshold
        )
        return None
    status = "confirmed" if rules_ok else "manual_review"
    logger.info("Match created %s/%s: confidence=%d status=%s", kalshi.market_id, polymarket.market_id, max(score, 0), status)
    return MarketMatch(kalshi, polymarket, max(score, 0), status, explanation)
