from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    allowed_origin: str = "http://localhost:8001"
    minimum_roi: float = 0.01
    minimum_match_confidence: int = 90
    # Market metadata (team names, rules text, the updated_at this is measured
    # against) only refreshes once per market_refresh_seconds - order-book prices
    # are always fetched live regardless. This must comfortably exceed
    # market_refresh_seconds or every opportunity gets marked stale for most of
    # each discovery cycle.
    stale_after_seconds: int = 600
    market_refresh_seconds: int = 300
    websocket_push_interval_seconds: float = 5.0
    target_stake_dollars: float = 100.0
    collector_timeout_seconds: float = 20.0
    collector_max_pages: int = 10
    enable_live_collectors: bool = True
    rate_limit_requests: int = 120
    rate_limit_window_seconds: float = 60.0
    kalshi_base_url: str = "https://external-api.kalshi.com/trade-api/v2"
    polymarket_base_url: str = "https://gamma-api.polymarket.com"
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

settings = Settings()
