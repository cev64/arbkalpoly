from dataclasses import replace
from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient

from backend.main import create_app
from backend.models.order_book import OrderBook, OrderBookLevel
from tests.test_market_discovery import market
from tests.test_matching_service import FakeKalshiCollector, FakePolymarketCollector
from tests.test_matching_service import market as matched_market


def matched_app(**kwargs):
    kalshi_collector = FakeKalshiCollector({
        "k1": OrderBook(yes_asks=(OrderBookLevel(0.47, 100),), no_asks=(OrderBookLevel(0.55, 100),)),
    })
    polymarket_collector = FakePolymarketCollector({
        ("p1-yes-token", "p1-no-token"): OrderBook(
            yes_asks=(OrderBookLevel(0.46, 100),), no_asks=(OrderBookLevel(0.49, 100),)
        ),
    })
    return create_app(
        start_collectors=False,
        kalshi_collector=kalshi_collector,
        polymarket_collector=polymarket_collector,
        **kwargs,
    )


def test_markets_endpoint_reads_normalized_cache():
    with TestClient(create_app(start_collectors=False)) as client:
        client.app.state.market_cache.upsert(market("kalshi", "k1"))
        response = client.get("/markets", params={"exchange": "kalshi"})

        assert response.status_code == 200
        assert response.json()[0]["market_id"] == "k1"
        assert "raw" not in response.json()[0]


def test_health_reports_collector_state():
    with TestClient(create_app(start_collectors=False)) as client:
        response = client.get("/health")

        assert response.status_code == 200
        assert response.json()["status"] == "ok"
        assert response.json()["market_count"] == 0


def test_matches_and_opportunities_reflect_cached_markets():
    with TestClient(matched_app()) as client:
        cache = client.app.state.market_cache
        cache.upsert(matched_market("kalshi", "k1", 0.47, 0.55))
        cache.upsert(matched_market("polymarket", "p1", 0.46, 0.49))

        matches_response = client.get("/matches")
        assert matches_response.status_code == 200
        assert len(matches_response.json()) == 1
        assert matches_response.json()[0]["status"] == "confirmed"

        opportunities_response = client.get("/opportunities")
        assert opportunities_response.status_code == 200
        body = opportunities_response.json()
        assert len(body) == 1
        assert body[0]["status"] == "confirmed"

        opportunity_id = body[0]["id"]
        detail_response = client.get(f"/opportunities/{opportunity_id}")
        assert detail_response.status_code == 200
        assert detail_response.json()["id"] == opportunity_id


def test_opportunities_filters_below_minimum_roi():
    with TestClient(matched_app()) as client:
        cache = client.app.state.market_cache
        cache.upsert(matched_market("kalshi", "k1", 0.47, 0.55))
        cache.upsert(matched_market("polymarket", "p1", 0.46, 0.49))

        response = client.get("/opportunities", params={"minimum_roi": 0.5})

        assert response.status_code == 200
        assert response.json() == []


def test_hide_stale_query_param_excludes_stale_opportunities():
    with TestClient(matched_app()) as client:
        cache = client.app.state.market_cache
        stale_kalshi = replace(
            matched_market("kalshi", "k1", 0.47, 0.55),
            updated_at=datetime.now(UTC) - timedelta(minutes=5),
        )
        cache.upsert(stale_kalshi)
        cache.upsert(matched_market("polymarket", "p1", 0.46, 0.49))

        default_response = client.get("/opportunities")
        assert default_response.status_code == 200
        assert default_response.json()[0]["status"] == "stale"

        hidden_response = client.get("/opportunities", params={"hide_stale": True})
        assert hidden_response.status_code == 200
        assert hidden_response.json() == []


def test_opportunities_websocket_streams_matched_opportunities():
    with TestClient(matched_app()) as client:
        cache = client.app.state.market_cache
        cache.upsert(matched_market("kalshi", "k1", 0.47, 0.55))
        cache.upsert(matched_market("polymarket", "p1", 0.46, 0.49))
        client.portal.call(client.app.state.opportunity_broadcaster.refresh_once)

        with client.websocket_connect("/ws/opportunities") as websocket:
            message = websocket.receive_json()

        assert len(message) == 1
        assert message[0]["status"] == "confirmed"


def test_opportunities_websocket_shares_one_snapshot_across_connections():
    with TestClient(matched_app()) as client:
        cache = client.app.state.market_cache
        cache.upsert(matched_market("kalshi", "k1", 0.47, 0.55))
        cache.upsert(matched_market("polymarket", "p1", 0.46, 0.49))
        client.portal.call(client.app.state.opportunity_broadcaster.refresh_once)

        with client.websocket_connect("/ws/opportunities") as first, client.websocket_connect("/ws/opportunities") as second:
            first_message = first.receive_json()
            second_message = second.receive_json()

        assert first_message == second_message
        assert len(first_message) == 1


def test_unknown_opportunity_id_returns_404():
    with TestClient(create_app(start_collectors=False)) as client:
        response = client.get("/opportunities/does-not-exist")

        assert response.status_code == 404
