from fastapi import APIRouter, Query, Request

from backend.config import settings
from backend.services.market_cache import MarketCache

router = APIRouter()


@router.get("/health")
def health(request: Request) -> dict:
    cache: MarketCache = request.app.state.market_cache
    discovery = request.app.state.market_discovery
    return {
        "status": "ok",
        "market_count": cache.count(),
        "collectors": discovery.status(),
    }


@router.get("/config/public")
def public_config() -> dict[str, float | int]:
    return {
        "minimum_roi": settings.minimum_roi,
        "minimum_match_confidence": settings.minimum_match_confidence,
        "stale_after_seconds": settings.stale_after_seconds,
        "market_refresh_seconds": settings.market_refresh_seconds,
    }


@router.get("/markets")
def markets(
    request: Request,
    exchange: str | None = None,
    sport: str | None = None,
    league: str | None = None,
    include_raw: bool = False,
    limit: int = Query(default=500, ge=1, le=2000),
) -> list[dict]:
    cache: MarketCache = request.app.state.market_cache
    return [
        cache.serialize(market, include_raw=include_raw)
        for market in cache.all(exchange=exchange, sport=sport, league=league)[:limit]
    ]


@router.get("/matches")
def matches() -> list[dict]:
    return []


@router.get("/opportunities")
def opportunities() -> list[dict]:
    return []
