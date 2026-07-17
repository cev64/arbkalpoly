from fastapi.testclient import TestClient

from backend.main import create_app


def test_requests_within_limit_succeed():
    with TestClient(create_app(start_collectors=False, rate_limit_requests=3, rate_limit_window_seconds=60)) as client:
        for _ in range(3):
            assert client.get("/health").status_code == 200


def test_exceeding_limit_returns_429_with_retry_after():
    with TestClient(create_app(start_collectors=False, rate_limit_requests=2, rate_limit_window_seconds=60)) as client:
        assert client.get("/health").status_code == 200
        assert client.get("/health").status_code == 200

        response = client.get("/health")

        assert response.status_code == 429
        assert "retry-after" in response.headers


def test_rate_limited_response_still_carries_cors_headers():
    with TestClient(create_app(start_collectors=False, rate_limit_requests=1, rate_limit_window_seconds=60)) as client:
        client.get("/health")

        response = client.get("/health", headers={"Origin": "http://localhost:8001"})

        assert response.status_code == 429
        assert response.headers.get("access-control-allow-origin") == "http://localhost:8001"
