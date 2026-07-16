from fastapi.testclient import TestClient

from backend.main import create_app
from tests.test_market_discovery import market


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
