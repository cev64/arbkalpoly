from datetime import UTC, datetime
from dataclasses import asdict

from backend.arbitrage.sizing import size_binary_arbitrage
from backend.matcher.market_matcher import MarketMatch
from backend.models.opportunity import Opportunity
from backend.models.order_book import OrderBook, OrderBookLevel


def _best_price(levels: tuple[OrderBookLevel, ...]) -> float:
    return min((level.price for level in levels), default=0.0)


class OpportunityService:
    def __init__(self, stale_after_seconds: int = 15) -> None:
        self.stale_after_seconds = stale_after_seconds

    def from_match(self, match: MarketMatch, kalshi_book: OrderBook, polymarket_book: OrderBook) -> list[Opportunity]:
        opportunities: list[Opportunity] = []
        last_updated = min(match.kalshi.updated_at, match.polymarket.updated_at)
        age_seconds = (datetime.now(UTC) - last_updated).total_seconds()
        status = "stale" if age_seconds > self.stale_after_seconds else match.status

        legs = [
            ("Kalshi", kalshi_book.yes_asks, "Polymarket", polymarket_book.no_asks, "YES", "NO"),
            ("Polymarket", polymarket_book.yes_asks, "Kalshi", kalshi_book.no_asks, "NO", "YES"),
        ]
        for yes_exchange, yes_asks, no_exchange, no_asks, kalshi_side, poly_side in legs:
            sizing = size_binary_arbitrage(yes_exchange, yes_asks, no_exchange, no_asks)
            if sizing.quantity <= 0 or sizing.net_profit <= 0:
                continue
            event = f"{match.kalshi.away_team} at {match.kalshi.home_team}"
            opportunities.append(Opportunity(
                id=f"{match.kalshi.market_id}:{match.polymarket.market_id}:{kalshi_side}:{poly_side}",
                sport=match.kalshi.sport,
                event=event,
                market=f"{match.kalshi.selection} to win",
                event_start=match.kalshi.event_start,
                kalshi_side=kalshi_side,
                kalshi_price=_best_price(kalshi_book.yes_asks if kalshi_side == "YES" else kalshi_book.no_asks),
                polymarket_side=poly_side,
                polymarket_price=_best_price(polymarket_book.no_asks if poly_side == "NO" else polymarket_book.yes_asks),
                gross_cost=sizing.gross_cost,
                estimated_fees=sizing.estimated_fees,
                net_edge=sizing.net_profit,
                roi=sizing.roi,
                maximum_executable_cost=sizing.gross_cost,
                maximum_expected_profit=sizing.net_profit,
                match_confidence=match.confidence,
                status=status,
                last_updated=last_updated,
                kalshi_url=match.kalshi.market_url,
                polymarket_url=match.polymarket.market_url,
            ))
        return opportunities

    @staticmethod
    def serialize(opportunity: Opportunity) -> dict:
        data = asdict(opportunity)
        data["event_start"] = opportunity.event_start.isoformat()
        data["last_updated"] = opportunity.last_updated.isoformat()
        return data
