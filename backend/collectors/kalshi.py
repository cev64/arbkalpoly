import re
from datetime import UTC, datetime
from typing import Any
from zoneinfo import ZoneInfo

import httpx

from backend.models.market import NormalizedMarket
from backend.models.order_book import OrderBook, OrderBookLevel
from backend.normalizer.sports_normalizer import normalize_team, parse_datetime

MLB_GAME_SERIES = "KXMLBGAME"


def _price(value: Any) -> float | None:
    if value is None or value == "":
        return None
    return float(value)


def _participants(title: str) -> tuple[str | None, str | None]:
    parts = re.split(r"\s+(?:vs\.?|at)\s+", title, maxsplit=1, flags=re.IGNORECASE)
    if len(parts) != 2:
        return None, None
    cleaned = [re.sub(r":\s*Game\s+\d+$", "", part, flags=re.IGNORECASE) for part in parts]
    return normalize_team(cleaned[0]), normalize_team(cleaned[1])


def _event_start(market: dict[str, Any]) -> datetime | None:
    rules = market.get("rules_primary") or ""
    scheduled = re.search(
        r"originally scheduled for ([A-Z][a-z]{2} \d{1,2}, \d{4}) at (\d{1,2}:\d{2} [AP]M) (?:EDT|EST)",
        rules,
    )
    if scheduled:
        local_time = datetime.strptime(
            f"{scheduled.group(1)} {scheduled.group(2)}",
            "%b %d, %Y %I:%M %p",
        )
        return local_time.replace(tzinfo=ZoneInfo("America/New_York"))

    start_value = market.get("occurrence_datetime") or market.get("expected_expiration_time")
    return parse_datetime(start_value) if start_value else None


def normalize_kalshi_event(event: dict[str, Any]) -> list[NormalizedMarket]:
    """Convert one Kalshi MLB game event into one binary market per team."""
    away_team, home_team = _participants(event.get("title", ""))
    normalized: list[NormalizedMarket] = []

    for market in event.get("markets") or []:
        event_start = _event_start(market)
        if event_start is None:
            continue

        selection = normalize_team(market.get("yes_sub_title"))
        if not selection:
            continue

        updated_value = (
            market.get("updated_time")
            or event.get("last_updated_ts")
            or datetime.now(UTC).isoformat()
        )
        rules_text = "\n\n".join(
            text.strip()
            for text in (market.get("rules_primary"), market.get("rules_secondary"))
            if text and text.strip()
        )
        ticker = str(market["ticker"])
        event_ticker = str(event["event_ticker"])

        normalized.append(NormalizedMarket(
            exchange="kalshi",
            market_id=ticker,
            sport="MLB",
            league="MLB",
            event_id=event_ticker,
            event_start=event_start,
            home_team=home_team,
            away_team=away_team,
            player=None,
            market_type="moneyline",
            selection=selection,
            line=None,
            period="full_game",
            yes_best_ask=_price(market.get("yes_ask_dollars")),
            yes_best_bid=_price(market.get("yes_bid_dollars")),
            no_best_ask=_price(market.get("no_ask_dollars")),
            no_best_bid=_price(market.get("no_bid_dollars")),
            rules_text=rules_text,
            market_url=f"https://kalshi.com/markets/{ticker}",
            updated_at=parse_datetime(updated_value),
            raw={"event": {key: value for key, value in event.items() if key != "markets"}, "market": market},
        ))

    return normalized


class KalshiCollector:
    """Read-only collector for public Kalshi MLB game-winner markets."""

    exchange = "kalshi"

    def __init__(
        self,
        base_url: str = "https://external-api.kalshi.com/trade-api/v2",
        timeout: float = 20.0,
        max_pages: int = 10,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self.base_url = base_url
        self.timeout = timeout
        self.max_pages = max_pages
        self.client = client

    async def fetch_markets(self) -> list[NormalizedMarket]:
        if self.client is not None:
            return await self._fetch(self.client)
        async with httpx.AsyncClient(
            base_url=self.base_url,
            timeout=self.timeout,
            headers={"User-Agent": "arbkalpoly/phase-1"},
        ) as client:
            return await self._fetch(client)

    async def _fetch(self, client: httpx.AsyncClient) -> list[NormalizedMarket]:
        cursor: str | None = None
        normalized: list[NormalizedMarket] = []

        for _ in range(self.max_pages):
            params: dict[str, str | int | bool] = {
                "series_ticker": MLB_GAME_SERIES,
                "status": "open",
                "with_nested_markets": True,
                "limit": 200,
            }
            if cursor:
                params["cursor"] = cursor
            response = await client.get("/events", params=params)
            response.raise_for_status()
            payload = response.json()
            for event in payload.get("events") or []:
                normalized.extend(normalize_kalshi_event(event))
            cursor = payload.get("cursor")
            if not cursor:
                break

        return normalized

    async def fetch_order_book(self, ticker: str) -> OrderBook:
        if self.client is not None:
            return await self._fetch_order_book(self.client, ticker)
        async with httpx.AsyncClient(
            base_url=self.base_url,
            timeout=self.timeout,
            headers={"User-Agent": "arbkalpoly/phase-1"},
        ) as client:
            return await self._fetch_order_book(client, ticker)

    async def _fetch_order_book(self, client: httpx.AsyncClient, ticker: str) -> OrderBook:
        response = await client.get(f"/markets/{ticker}/orderbook")
        response.raise_for_status()
        payload = response.json().get("orderbook_fp") or {}
        yes_bids = payload.get("yes_dollars") or []
        no_bids = payload.get("no_dollars") or []

        # Kalshi's public book only exposes resting bids; the ask side of one
        # outcome is the complement of the other outcome's bid at the same size.
        yes_asks = tuple(
            OrderBookLevel(price=round(1 - float(price), 6), quantity=float(quantity))
            for price, quantity in no_bids
        )
        no_asks = tuple(
            OrderBookLevel(price=round(1 - float(price), 6), quantity=float(quantity))
            for price, quantity in yes_bids
        )
        return OrderBook(yes_asks=yes_asks, no_asks=no_asks)
