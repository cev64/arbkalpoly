import asyncio
import json
from pathlib import Path

import httpx

from backend.collectors.kalshi import KalshiCollector, normalize_kalshi_event
from backend.collectors.polymarket import PolymarketCollector, normalize_polymarket_event
from backend.models.order_book import OrderBookLevel

FIXTURES = Path(__file__).parent / "fixtures"


def fixture(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text())


def test_normalize_kalshi_mlb_game():
    markets = normalize_kalshi_event(fixture("kalshi_mlb_event.json"))

    assert len(markets) == 2
    assert markets[0].away_team == "St. Louis Cardinals"
    assert markets[0].home_team == "Arizona Diamondbacks"
    assert markets[0].selection == "St. Louis Cardinals"
    assert markets[0].yes_best_ask == 0.46
    assert "remains open" in markets[0].rules_text


def test_kalshi_prefers_scheduled_rule_time_and_cleans_doubleheader_suffix():
    event = fixture("kalshi_mlb_event.json")
    event["title"] = "Tampa Bay vs Boston: Game 1"
    event["markets"] = [event["markets"][0]]
    event["markets"][0]["yes_sub_title"] = "Boston"
    event["markets"][0]["rules_primary"] = (
        "If Boston wins the game originally scheduled for Jul 17, 2026 at 1:35 PM EDT, "
        "then the market resolves to Yes."
    )

    normalized = normalize_kalshi_event(event)[0]

    assert normalized.home_team == "Boston Red Sox"
    assert normalized.event_start.isoformat() == "2026-07-17T13:35:00-04:00"


def test_normalize_polymarket_mlb_moneyline():
    markets = normalize_polymarket_event(fixture("polymarket_mlb_event.json"))

    assert len(markets) == 2
    assert markets[0].selection == "Tampa Bay Rays"
    assert markets[0].yes_best_bid == 0.45
    assert markets[0].yes_best_ask == 0.46
    assert markets[1].selection == "Boston Red Sox"
    assert markets[1].yes_best_bid == 0.54
    assert markets[1].yes_best_ask == 0.55


def test_collectors_use_public_paginated_endpoints():
    kalshi_event = fixture("kalshi_mlb_event.json")
    poly_event = fixture("polymarket_mlb_event.json")

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.host == "kalshi.test":
            assert request.url.params["series_ticker"] == "KXMLBGAME"
            return httpx.Response(200, json={"events": [kalshi_event], "cursor": ""})
        assert request.url.params["tag_slug"] == "mlb"
        return httpx.Response(200, json={"events": [poly_event], "next_cursor": ""})

    async def collect():
        transport = httpx.MockTransport(handler)
        async with httpx.AsyncClient(transport=transport, base_url="https://kalshi.test") as kalshi_client:
            kalshi = await KalshiCollector(client=kalshi_client).fetch_markets()
        async with httpx.AsyncClient(transport=transport, base_url="https://poly.test") as poly_client:
            poly = await PolymarketCollector(client=poly_client).fetch_markets()
        return kalshi, poly

    kalshi, poly = asyncio.run(collect())
    assert len(kalshi) == 2
    assert len(poly) == 2


def test_kalshi_order_book_derives_asks_from_opposite_side_bids():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/markets/KXMLBGAME-TEST-STL/orderbook"
        return httpx.Response(200, json={
            "orderbook_fp": {
                "yes_dollars": [["0.40", "74.00"], ["0.39", "10.00"]],
                "no_dollars": [["0.54", "2.00"], ["0.06", "1897.00"]],
            }
        })

    async def collect():
        transport = httpx.MockTransport(handler)
        async with httpx.AsyncClient(transport=transport, base_url="https://kalshi.test") as client:
            return await KalshiCollector(client=client).fetch_order_book("KXMLBGAME-TEST-STL")

    book = asyncio.run(collect())

    assert (0.46, 2.0) in [(level.price, level.quantity) for level in book.yes_asks]
    assert (0.60, 74.0) in [(level.price, level.quantity) for level in book.no_asks]


def test_polymarket_order_book_reads_both_token_books():
    def handler(request: httpx.Request) -> httpx.Response:
        token_id = request.url.params["token_id"]
        if token_id == "yes-token":
            return httpx.Response(200, json={"bids": [], "asks": [{"price": "0.46", "size": "100"}]})
        assert token_id == "no-token"
        return httpx.Response(200, json={"bids": [], "asks": [{"price": "0.55", "size": "50"}]})

    async def collect():
        transport = httpx.MockTransport(handler)
        async with httpx.AsyncClient(transport=transport, base_url="https://clob.test") as client:
            return await PolymarketCollector(client=client).fetch_order_book("yes-token", "no-token")

    book = asyncio.run(collect())

    assert book.yes_asks == (OrderBookLevel(0.46, 100.0),)
    assert book.no_asks == (OrderBookLevel(0.55, 50.0),)


def test_polymarket_token_ids_reads_raw_metadata():
    markets = normalize_polymarket_event(fixture("polymarket_mlb_event.json"))

    token_ids = PolymarketCollector.token_ids(markets[0])

    assert token_ids is not None
    own, opposing = token_ids
    assert own != opposing
