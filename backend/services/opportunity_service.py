from datetime import datetime
from dataclasses import asdict

from backend.arbitrage.sizing import size_binary_arbitrage
from backend.matcher.market_matcher import MarketMatch, event_label
from backend.models.opportunity import Opportunity
from backend.models.order_book import OrderBook, OrderBookLevel


def _best_price(levels: tuple[OrderBookLevel, ...]) -> float:
    return min((level.price for level in levels), default=0.0)


class OpportunityService:
    def __init__(self, target_stake_dollars: float = 100.0) -> None:
        self.target_stake_dollars = target_stake_dollars

    def from_match(
        self,
        match: MarketMatch,
        kalshi_book: OrderBook,
        polymarket_book: OrderBook,
        last_updated: datetime,
        is_stale: bool,
    ) -> list[Opportunity]:
        opportunities: list[Opportunity] = []
        status = "stale" if is_stale else match.status

        legs = [
            ("Kalshi", kalshi_book.yes_asks, "Polymarket", polymarket_book.no_asks, "YES", "NO"),
            ("Polymarket", polymarket_book.yes_asks, "Kalshi", kalshi_book.no_asks, "NO", "YES"),
        ]
        for yes_exchange, yes_asks, no_exchange, no_asks, kalshi_side, poly_side in legs:
            max_sizing = size_binary_arbitrage(yes_exchange, yes_asks, no_exchange, no_asks)
            if max_sizing.quantity <= 0 or max_sizing.net_profit <= 0:
                continue

            # Reporting the full executable depth (which can be thousands of
            # dollars) isn't how anyone actually places these bets - size a
            # practical default position instead: target_stake_dollars on
            # whichever leg is pricier (so the complementary leg, being cheaper
            # per contract, never costs more than that), capped by real depth.
            anchor_price = max(_best_price(yes_asks), _best_price(no_asks))
            target_quantity = self.target_stake_dollars / anchor_price if anchor_price > 0 else max_sizing.quantity
            sizing = size_binary_arbitrage(
                yes_exchange, yes_asks, no_exchange, no_asks, max_quantity=min(target_quantity, max_sizing.quantity)
            )
            if sizing.quantity <= 0 or sizing.net_profit <= 0:
                continue

            if yes_exchange == "Kalshi":
                kalshi_stake, kalshi_fee = sizing.yes_cost, sizing.yes_fee
                polymarket_stake, polymarket_fee = sizing.no_cost, sizing.no_fee
            else:
                kalshi_stake, kalshi_fee = sizing.no_cost, sizing.no_fee
                polymarket_stake, polymarket_fee = sizing.yes_cost, sizing.yes_fee
            event = event_label(match.kalshi)
            opportunities.append(Opportunity(
                id=f"{match.kalshi.market_id}:{match.polymarket.market_id}:{kalshi_side}:{poly_side}",
                sport=match.kalshi.sport,
                event=event,
                market=f"{match.kalshi.selection} to win",
                event_start=match.kalshi.event_start,
                kalshi_side=kalshi_side,
                kalshi_price=_best_price(kalshi_book.yes_asks if kalshi_side == "YES" else kalshi_book.no_asks),
                kalshi_stake=kalshi_stake,
                kalshi_fee=kalshi_fee,
                polymarket_side=poly_side,
                polymarket_price=_best_price(polymarket_book.no_asks if poly_side == "NO" else polymarket_book.yes_asks),
                polymarket_stake=polymarket_stake,
                polymarket_fee=polymarket_fee,
                contracts=sizing.quantity,
                gross_cost=sizing.gross_cost,
                estimated_fees=sizing.estimated_fees,
                net_edge=sizing.net_profit,
                roi=sizing.roi,
                maximum_executable_cost=max_sizing.gross_cost,
                maximum_expected_profit=max_sizing.net_profit,
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

    @staticmethod
    def serialize_detail(
        opportunity: Opportunity, match: MarketMatch, kalshi_book: OrderBook, polymarket_book: OrderBook
    ) -> dict:
        data = OpportunityService.serialize(opportunity)
        data["kalshi_rules_text"] = match.kalshi.rules_text
        data["polymarket_rules_text"] = match.polymarket.rules_text
        data["match_explanation"] = match.explanation
        data["kalshi_order_book"] = _serialize_order_book(kalshi_book)
        data["polymarket_order_book"] = _serialize_order_book(polymarket_book)
        return data


def _serialize_order_book(book: OrderBook) -> dict:
    return {
        "yes_asks": [
            {"price": level.price, "quantity": level.quantity}
            for level in sorted(book.yes_asks, key=lambda level: level.price)
        ],
        "no_asks": [
            {"price": level.price, "quantity": level.quantity}
            for level in sorted(book.no_asks, key=lambda level: level.price)
        ],
    }
