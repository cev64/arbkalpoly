from itertools import product

from backend.matcher.market_matcher import MarketMatch, match_markets
from backend.models.opportunity import Opportunity
from backend.services.market_cache import MarketCache
from backend.services.opportunity_service import OpportunityService


class MatchingService:
    """Builds cross-exchange market matches and arbitrage opportunities from the live market cache."""

    def __init__(self, match_confidence_threshold: int = 90) -> None:
        self.match_confidence_threshold = match_confidence_threshold
        self._opportunity_service = OpportunityService()

    def find_matches(self, cache: MarketCache) -> list[MarketMatch]:
        kalshi_markets = cache.all(exchange="kalshi")
        polymarket_markets = cache.all(exchange="polymarket")

        matches: list[MarketMatch] = []
        for kalshi_market, polymarket_market in product(kalshi_markets, polymarket_markets):
            if kalshi_market.league != polymarket_market.league:
                continue
            if kalshi_market.event_start.date() != polymarket_market.event_start.date():
                continue
            match = match_markets(kalshi_market, polymarket_market, threshold=self.match_confidence_threshold)
            if match is not None:
                matches.append(match)
        return matches

    def find_opportunities(self, cache: MarketCache) -> list[Opportunity]:
        opportunities: list[Opportunity] = []
        for match in self.find_matches(cache):
            opportunities.extend(self._opportunity_service.from_match(match))
        return opportunities

    @staticmethod
    def serialize_match(match: MarketMatch) -> dict:
        return {
            "kalshi_market_id": match.kalshi.market_id,
            "polymarket_market_id": match.polymarket.market_id,
            "sport": match.kalshi.sport,
            "league": match.kalshi.league,
            "event": f"{match.kalshi.away_team} at {match.kalshi.home_team}",
            "market_type": match.kalshi.market_type,
            "selection": match.kalshi.selection,
            "confidence": match.confidence,
            "status": match.status,
            "explanation": match.explanation,
        }
