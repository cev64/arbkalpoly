from fastapi.testclient import TestClient

from backend.main import create_app
from tests.test_market_discovery import market
from tests.test_matching_service import market as matched_market


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
    with TestClient(create_app(start_collectors=False)) as client:
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
    with TestClient(create_app(start_collectors=False)) as client:
        cache = client.app.state.market_cache
        cache.upsert(matched_market("kalshi", "k1", 0.47, 0.55))
        cache.upsert(matched_market("polymarket", "p1", 0.46, 0.49))

        response = client.get("/opportunities", params={"minimum_roi": 0.5})

        assert response.status_code == 200
        assert response.json() == []


def test_unknown_opportunity_id_returns_404():
    with TestClient(create_app(start_collectors=False)) as client:
        response = client.get("/opportunities/does-not-exist")

        assert response.status_code == 404
