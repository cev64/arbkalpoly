import asyncio
import json
import re
from datetime import UTC, datetime, timedelta
from typing import Any

import httpx

from backend.models.market import NormalizedMarket
from backend.models.order_book import OrderBook, OrderBookLevel
from backend.normalizer.sports_normalizer import normalize_player, normalize_team, parse_datetime


def _list(value: Any) -> list[Any]:
    if isinstance(value, list):
        return value
    if isinstance(value, str):
        parsed = json.loads(value)
        return parsed if isinstance(parsed, list) else []
    return []


def _price(value: Any) -> float | None:
    if value is None or value == "":
        return None
    return float(value)


def _complement(value: float | None) -> float | None:
    return round(1.0 - value, 6) if value is not None else None


def _event_teams(event: dict[str, Any]) -> tuple[str | None, str | None]:
    teams = event.get("teams") or []
    away = next((team.get("name") for team in teams if team.get("ordering") == "away"), None)
    home = next((team.get("name") for team in teams if team.get("ordering") == "home"), None)
    if away and home:
        return normalize_team(away), normalize_team(home)

    parts = re.split(r"\s+(?:vs\.?|at)\s+", event.get("title", ""), maxsplit=1, flags=re.IGNORECASE)
    if len(parts) == 2:
        return normalize_team(parts[0]), normalize_team(parts[1])
    return None, None


def normalize_polymarket_event(event: dict[str, Any]) -> list[NormalizedMarket]:
    """Convert one Polymarket MLB event into a binary view for each team outcome."""
    away_team, home_team = _event_teams(event)
    start_value = event.get("startTime") or event.get("eventDate") or event.get("startDate")
    if not start_value:
        return []

    normalized: list[NormalizedMarket] = []
    for market in event.get("markets") or []:
        if market.get("sportsMarketType") != "moneyline":
            continue

        outcomes = _list(market.get("outcomes"))
        token_ids = _list(market.get("clobTokenIds"))
        if len(outcomes) != 2:
            continue
        if len(token_ids) != 2:
            token_ids = [f"outcome-{index}" for index in range(2)]

        first_bid = _price(market.get("bestBid"))
        first_ask = _price(market.get("bestAsk"))
        updated_value = (
            market.get("updatedAt")
            or event.get("updatedAt")
            or datetime.now(UTC).isoformat()
        )
        rules_text = "\n\n".join(
            text.strip()
            for text in (market.get("description"), market.get("resolutionSource"))
            if text and text.strip()
        )
        event_slug = event.get("slug") or event.get("id")

        for index, outcome in enumerate(outcomes):
            if index == 0:
                yes_bid, yes_ask = first_bid, first_ask
                no_bid, no_ask = _complement(first_ask), _complement(first_bid)
            else:
                yes_bid, yes_ask = _complement(first_ask), _complement(first_bid)
                no_bid, no_ask = first_bid, first_ask

            selection = normalize_team(str(outcome))
            if not selection:
                continue
            market_id = f"{market['id']}:{token_ids[index]}"
            normalized.append(NormalizedMarket(
                exchange="polymarket",
                market_id=market_id,
                sport="MLB",
                league="MLB",
                event_id=str(event.get("gameId") or event["id"]),
                event_start=parse_datetime(start_value),
                home_team=home_team,
                away_team=away_team,
                player=None,
                market_type="moneyline",
                selection=selection,
                line=None,
                period="full_game",
                yes_best_ask=yes_ask,
                yes_best_bid=yes_bid,
                no_best_ask=no_ask,
                no_best_bid=no_bid,
                rules_text=rules_text,
                market_url=f"https://polymarket.com/event/{event_slug}",
                updated_at=parse_datetime(updated_value),
                raw={
                    "event": {key: value for key, value in event.items() if key != "markets"},
                    "market": market,
                    "outcome_index": index,
                    "token_id": token_ids[index],
                    "opposing_token_id": token_ids[1 - index],
                },
            ))

    return normalized


def _polymarket_tournament_name(event: dict[str, Any]) -> str | None:
    """Derive a canonical tournament name matching Kalshi's own stripped sub_title."""
    title = event.get("title") or ""
    without_prefix = re.sub(r"^PGA Tour:\s*", "", title, flags=re.IGNORECASE)
    without_suffix = re.sub(r"[:\s]*Winner$", "", without_prefix, flags=re.IGNORECASE).strip()
    return without_suffix or None


def normalize_polymarket_tournament_event(event: dict[str, Any]) -> list[NormalizedMarket]:
    """Convert one Polymarket golf tournament-winner event into a binary market per golfer.

    Unlike MLB, each market here is already a standalone Yes/No pair for one golfer
    (its own two clobTokenIds), not two outcomes sharing one market object, so there's
    no complement trick needed to build the "no" side - it's this golfer's own token.
    """
    tournament = _polymarket_tournament_name(event)
    start_value = event.get("endDate") or event.get("startTime") or event.get("eventDate")
    if not tournament or not start_value:
        return []

    normalized: list[NormalizedMarket] = []
    for market in event.get("markets") or []:
        outcomes = _list(market.get("outcomes"))
        token_ids = _list(market.get("clobTokenIds"))
        if outcomes != ["Yes", "No"] or len(token_ids) != 2:
            continue

        golfer = normalize_player(market.get("groupItemTitle"))
        if not golfer:
            continue

        yes_token_id, no_token_id = token_ids
        yes_bid = _price(market.get("bestBid"))
        yes_ask = _price(market.get("bestAsk"))
        updated_value = market.get("updatedAt") or event.get("updatedAt") or datetime.now(UTC).isoformat()
        rules_text = "\n\n".join(
            text.strip()
            for text in (market.get("description"), market.get("resolutionSource"))
            if text and text.strip()
        )
        event_slug = event.get("slug") or event.get("id")

        normalized.append(NormalizedMarket(
            exchange="polymarket",
            market_id=f"{market['id']}:{yes_token_id}",
            sport="GOLF",
            league="GOLF",
            event_id=str(event.get("id")),
            event_start=parse_datetime(start_value),
            home_team=tournament,
            away_team=None,
            player=golfer,
            market_type="tournament_winner",
            selection=golfer,
            line=None,
            period="tournament",
            yes_best_ask=yes_ask,
            yes_best_bid=yes_bid,
            no_best_ask=_complement(yes_bid),
            no_best_bid=_complement(yes_ask),
            rules_text=rules_text,
            market_url=f"https://polymarket.com/event/{event_slug}",
            updated_at=parse_datetime(updated_value),
            raw={
                "event": {key: value for key, value in event.items() if key != "markets"},
                "market": market,
                "token_id": yes_token_id,
                "opposing_token_id": no_token_id,
            },
        ))

    return normalized


class PolymarketCollector:
    """Read-only collector for public Polymarket MLB game-winner markets."""

    exchange = "polymarket"

    def __init__(
        self,
        base_url: str = "https://gamma-api.polymarket.com",
        clob_base_url: str = "https://clob.polymarket.com",
        timeout: float = 20.0,
        max_pages: int = 10,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self.base_url = base_url
        self.clob_base_url = clob_base_url
        self.timeout = timeout
        self.max_pages = max_pages
        self.client = client

    @staticmethod
    def token_ids(market: NormalizedMarket) -> tuple[str, str] | None:
        """Return (own_token_id, opposing_token_id) for a normalized Polymarket market, if known."""
        if not market.raw:
            return None
        own = market.raw.get("token_id")
        opposing = market.raw.get("opposing_token_id")
        if own is None or opposing is None:
            return None
        return str(own), str(opposing)

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
        normalized: list[NormalizedMarket] = []
        normalized.extend(await self._fetch_mlb(client))
        normalized.extend(await self._fetch_golf(client))
        return normalized

    async def _fetch_mlb(self, client: httpx.AsyncClient) -> list[NormalizedMarket]:
        cursor: str | None = None
        normalized: list[NormalizedMarket] = []
        start_time_min = (datetime.now(UTC) - timedelta(days=1)).isoformat()

        for _ in range(self.max_pages):
            params: dict[str, str | int | bool] = {
                "tag_slug": "mlb",
                "active": True,
                "closed": False,
                "start_time_min": start_time_min,
                "limit": 100,
            }
            if cursor:
                params["after_cursor"] = cursor
            response = await client.get("/events/keyset", params=params)
            response.raise_for_status()
            payload = response.json()
            for event in payload.get("events") or []:
                if str(event.get("seriesSlug", "")).lower() == "mlb":
                    normalized.extend(normalize_polymarket_event(event))
            cursor = payload.get("next_cursor")
            if not cursor:
                break

        return normalized

    async def _fetch_golf(self, client: httpx.AsyncClient) -> list[NormalizedMarket]:
        cursor: str | None = None
        normalized: list[NormalizedMarket] = []

        for _ in range(self.max_pages):
            params: dict[str, str | int | bool] = {
                "tag_slug": "golf",
                "active": True,
                "closed": False,
                "limit": 100,
            }
            if cursor:
                params["after_cursor"] = cursor
            response = await client.get("/events/keyset", params=params)
            response.raise_for_status()
            payload = response.json()
            for event in payload.get("events") or []:
                # Only tournament-winner events, not the top5/top10/make-the-cut
                # prop markets that share the same "golf" tag.
                if str(event.get("slug", "")).endswith("-winner"):
                    normalized.extend(normalize_polymarket_tournament_event(event))
            cursor = payload.get("next_cursor")
            if not cursor:
                break

        return normalized

    async def fetch_order_book(self, yes_token_id: str, no_token_id: str) -> OrderBook:
        if self.client is not None:
            return await self._fetch_order_book(self.client, yes_token_id, no_token_id)
        async with httpx.AsyncClient(
            base_url=self.clob_base_url,
            timeout=self.timeout,
            headers={"User-Agent": "arbkalpoly/phase-1"},
        ) as client:
            return await self._fetch_order_book(client, yes_token_id, no_token_id)

    async def _fetch_order_book(
        self, client: httpx.AsyncClient, yes_token_id: str, no_token_id: str
    ) -> OrderBook:
        yes_response, no_response = await asyncio.gather(
            client.get("/book", params={"token_id": yes_token_id}),
            client.get("/book", params={"token_id": no_token_id}),
        )
        yes_response.raise_for_status()
        no_response.raise_for_status()
        return OrderBook(
            yes_asks=_levels(yes_response.json().get("asks") or []),
            no_asks=_levels(no_response.json().get("asks") or []),
        )


def _levels(raw_levels: list[dict[str, Any]]) -> tuple[OrderBookLevel, ...]:
    return tuple(
        OrderBookLevel(price=float(level["price"]), quantity=float(level["size"]))
        for level in raw_levels
    )
