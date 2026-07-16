import asyncio
import logging
from itertools import product
from typing import Protocol

from backend.collectors.polymarket import PolymarketCollector
from backend.matcher.market_matcher import MarketMatch, match_markets
from backend.models.opportunity import Opportunity
from backend.services.market_cache import MarketCache
from backend.services.opportunity_service import OpportunityService

logger = logging.getLogger(__name__)


class KalshiOrderBookSource(Protocol):
    async def fetch_order_book(self, ticker: str): ...


class PolymarketOrderBookSource(Protocol):
    async def fetch_order_book(self, yes_token_id: str, no_token_id: str): ...


class MatchingService:
    """Builds cross-exchange market matches and arbitrage opportunities from the live market cache."""

    def __init__(
        self,
        kalshi_collector: KalshiOrderBookSource,
        polymarket_collector: PolymarketOrderBookSource,
        match_confidence_threshold: int = 90,
        stale_after_seconds: int = 15,
    ) -> None:
        self.kalshi_collector = kalshi_collector
        self.polymarket_collector = polymarket_collector
        self.match_confidence_threshold = match_confidence_threshold
        self._opportunity_service = OpportunityService(stale_after_seconds=stale_after_seconds)

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

    async def find_opportunities(self, cache: MarketCache) -> list[Opportunity]:
        matches = self.find_matches(cache)
        books = await asyncio.gather(*(self._fetch_books(match) for match in matches))

        opportunities: list[Opportunity] = []
        for match, book_pair in zip(matches, books):
            if book_pair is None:
                continue
            kalshi_book, polymarket_book = book_pair
            opportunities.extend(self._opportunity_service.from_match(match, kalshi_book, polymarket_book))
        return opportunities

    async def _fetch_books(self, match: MarketMatch):
        token_ids = PolymarketCollector.token_ids(match.polymarket)
        if token_ids is None:
            logger.warning(
                "Skipping match %s/%s: Polymarket token metadata missing",
                match.kalshi.market_id,
                match.polymarket.market_id,
            )
            return None
        yes_token_id, no_token_id = token_ids
        try:
            return await asyncio.gather(
                self.kalshi_collector.fetch_order_book(match.kalshi.market_id),
                self.polymarket_collector.fetch_order_book(yes_token_id, no_token_id),
            )
        except Exception as error:
            logger.error(
                "Order book fetch failed for %s/%s: %s", match.kalshi.market_id, match.polymarket.market_id, error
            )
            return None

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
