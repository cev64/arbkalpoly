import asyncio
import logging
from collections import defaultdict
from datetime import UTC, date, datetime
from typing import Protocol

from backend.collectors.polymarket import PolymarketCollector
from backend.matcher.market_matcher import MarketMatch, event_label, match_markets
from backend.models.market import NormalizedMarket
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
        target_stake_dollars: float = 100.0,
    ) -> None:
        self.kalshi_collector = kalshi_collector
        self.polymarket_collector = polymarket_collector
        self.match_confidence_threshold = match_confidence_threshold
        self.stale_after_seconds = stale_after_seconds
        self._opportunity_service = OpportunityService(target_stake_dollars=target_stake_dollars)

    def _freshness(self, cache: MarketCache) -> tuple[datetime, bool]:
        """How long since discovery last successfully refreshed both exchanges.

        Deliberately not per-market: an exchange's own per-market timestamp reflects
        when that market's price last changed there (routinely hours old for an
        illiquid market), not whether our own discovery pipeline is still healthy.
        """
        now = datetime.now(UTC)
        kalshi_refreshed = cache.last_refreshed("kalshi") or now
        polymarket_refreshed = cache.last_refreshed("polymarket") or now
        last_updated = min(kalshi_refreshed, polymarket_refreshed)
        is_stale = (now - last_updated).total_seconds() > self.stale_after_seconds
        return last_updated, is_stale

    def find_matches(self, cache: MarketCache) -> list[MarketMatch]:
        kalshi_markets = cache.all(exchange="kalshi")
        polymarket_markets = cache.all(exchange="polymarket")

        # Two markets can only ever match if they're the same selection (team or
        # golfer) on the same calendar day in the same league, so bucket on all
        # three instead of comparing every Kalshi market against every Polymarket
        # market. (league, date) alone was fine for MLB's 2-teams-per-game scale,
        # but a golf tournament field is ~150 players sharing one (league, date)
        # bucket - that's ~20,000 candidate pairs per tournament, re-evaluated
        # (and logged) on every 5-second broadcaster tick.
        polymarket_by_key: dict[tuple[str, date, str], list[NormalizedMarket]] = defaultdict(list)
        for polymarket_market in polymarket_markets:
            key = (polymarket_market.league, polymarket_market.event_start.date(), polymarket_market.selection)
            polymarket_by_key[key].append(polymarket_market)

        matches: list[MarketMatch] = []
        for kalshi_market in kalshi_markets:
            key = (kalshi_market.league, kalshi_market.event_start.date(), kalshi_market.selection)
            for polymarket_market in polymarket_by_key.get(key, ()):
                match = match_markets(kalshi_market, polymarket_market, threshold=self.match_confidence_threshold)
                if match is not None:
                    matches.append(match)
        return matches

    async def find_opportunities(self, cache: MarketCache) -> list[Opportunity]:
        matches = self.find_matches(cache)
        books = await asyncio.gather(*(self._fetch_books(match) for match in matches))
        last_updated, is_stale = self._freshness(cache)
        if is_stale:
            logger.warning("Market discovery data is stale: last refreshed %s", last_updated.isoformat())

        opportunities: list[Opportunity] = []
        for match, book_pair in zip(matches, books):
            if book_pair is None:
                continue
            kalshi_book, polymarket_book = book_pair
            opportunities.extend(
                self._opportunity_service.from_match(match, kalshi_book, polymarket_book, last_updated, is_stale)
            )

        opportunities.sort(key=lambda opportunity: opportunity.roi, reverse=True)
        logger.info("Computed %d opportunities from %d matches", len(opportunities), len(matches))
        return opportunities

    async def find_opportunity_detail(self, cache: MarketCache, opportunity_id: str) -> dict | None:
        matches = self.find_matches(cache)
        books = await asyncio.gather(*(self._fetch_books(match) for match in matches))
        last_updated, is_stale = self._freshness(cache)

        for match, book_pair in zip(matches, books):
            if book_pair is None:
                continue
            kalshi_book, polymarket_book = book_pair
            for opportunity in self._opportunity_service.from_match(
                match, kalshi_book, polymarket_book, last_updated, is_stale
            ):
                if opportunity.id == opportunity_id:
                    return self._opportunity_service.serialize_detail(opportunity, match, kalshi_book, polymarket_book)
        return None

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
            "event": event_label(match.kalshi),
            "market_type": match.kalshi.market_type,
            "selection": match.kalshi.selection,
            "confidence": match.confidence,
            "status": match.status,
            "explanation": match.explanation,
        }
