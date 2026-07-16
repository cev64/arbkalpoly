from dataclasses import dataclass
from backend.matcher.rule_validator import validate_rules
from backend.models.market import NormalizedMarket

@dataclass(frozen=True)
class MarketMatch:
    kalshi: NormalizedMarket
    polymarket: NormalizedMarket
    confidence: int
    status: str
    explanation: str

def match_markets(kalshi: NormalizedMarket, polymarket: NormalizedMarket, threshold: int = 90) -> MarketMatch | None:
    score = 100
    checks = [
        kalshi.league == polymarket.league,
        kalshi.home_team == polymarket.home_team,
        kalshi.away_team == polymarket.away_team,
        kalshi.event_start.date() == polymarket.event_start.date(),
        kalshi.market_type == polymarket.market_type,
        kalshi.selection == polymarket.selection,
        kalshi.line == polymarket.line,
        kalshi.period == polymarket.period,
    ]
    score -= checks.count(False) * 15
    rules_ok, explanation = validate_rules(kalshi.rules_text, polymarket.rules_text)
    if not rules_ok:
        score -= 20
    if score < threshold:
        return None
    return MarketMatch(kalshi, polymarket, max(score, 0), "confirmed" if rules_ok else "manual_review", explanation)
