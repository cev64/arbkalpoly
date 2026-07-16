from datetime import UTC, datetime
from dataclasses import asdict
from backend.arbitrage.calculator import calculate_binary_arbitrage
from backend.matcher.market_matcher import MarketMatch
from backend.models.opportunity import Opportunity

class OpportunityService:
    def from_match(self, match: MarketMatch) -> list[Opportunity]:
        opportunities: list[Opportunity] = []
        pairs = [
            ("Kalshi", match.kalshi.yes_best_ask, "Polymarket", match.polymarket.no_best_ask, "YES", "NO"),
            ("Polymarket", match.polymarket.yes_best_ask, "Kalshi", match.kalshi.no_best_ask, "NO", "YES"),
        ]
        for yes_exchange, yes_price, no_exchange, no_price, kalshi_side, poly_side in pairs:
            if yes_price is None or no_price is None:
                continue
            result = calculate_binary_arbitrage(yes_exchange, yes_price, no_exchange, no_price)
            if not result.profitable:
                continue
            event = f"{match.kalshi.away_team} at {match.kalshi.home_team}"
            opportunities.append(Opportunity(
                id=f"{match.kalshi.market_id}:{match.polymarket.market_id}:{kalshi_side}:{poly_side}",
                sport=match.kalshi.sport,
                event=event,
                market=f"{match.kalshi.selection} to win",
                event_start=match.kalshi.event_start,
                kalshi_side=kalshi_side,
                kalshi_price=match.kalshi.yes_best_ask if kalshi_side == "YES" else match.kalshi.no_best_ask or 0,
                polymarket_side=poly_side,
                polymarket_price=match.polymarket.no_best_ask if poly_side == "NO" else match.polymarket.yes_best_ask or 0,
                gross_cost=result.gross_cost,
                estimated_fees=result.estimated_fees,
                net_edge=result.net_profit,
                roi=result.roi,
                maximum_executable_cost=result.gross_cost,
                maximum_expected_profit=result.net_profit,
                match_confidence=match.confidence,
                status=match.status,
                last_updated=datetime.now(UTC),
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
