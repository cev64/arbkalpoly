from fastapi import APIRouter, HTTPException, Query, Request

from backend.config import settings
from backend.services.market_cache import MarketCache
from backend.services.matching_service import MatchingService
from backend.services.opportunity_service import OpportunityService

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
def matches(request: Request) -> list[dict]:
    cache: MarketCache = request.app.state.market_cache
    matching_service: MatchingService = request.app.state.matching_service
    return [MatchingService.serialize_match(match) for match in matching_service.find_matches(cache)]


@router.get("/opportunities")
def opportunities(
    request: Request,
    sport: str | None = None,
    minimum_roi: float | None = None,
    minimum_match_confidence: int | None = None,
) -> list[dict]:
    cache: MarketCache = request.app.state.market_cache
    matching_service: MatchingService = request.app.state.matching_service
    roi_floor = settings.minimum_roi if minimum_roi is None else minimum_roi
    confidence_floor = settings.minimum_match_confidence if minimum_match_confidence is None else minimum_match_confidence

    results = matching_service.find_opportunities(cache)
    if sport:
        results = [item for item in results if item.sport.lower() == sport.lower()]
    results = [item for item in results if item.roi >= roi_floor and item.match_confidence >= confidence_floor]
    return [OpportunityService.serialize(item) for item in results]


@router.get("/opportunities/{opportunity_id}")
def opportunity(opportunity_id: str, request: Request) -> dict:
    cache: MarketCache = request.app.state.market_cache
    matching_service: MatchingService = request.app.state.matching_service
    for item in matching_service.find_opportunities(cache):
        if item.id == opportunity_id:
            return OpportunityService.serialize(item)
    raise HTTPException(status_code=404, detail="Opportunity not found")
