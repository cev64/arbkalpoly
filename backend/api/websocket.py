import asyncio

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from backend.services.market_cache import MarketCache
from backend.services.matching_service import MatchingService
from backend.services.opportunity_service import OpportunityService

router = APIRouter()


@router.websocket("/ws/opportunities")
async def stream_opportunities(websocket: WebSocket) -> None:
    await websocket.accept()
    cache: MarketCache = websocket.app.state.market_cache
    matching_service: MatchingService = websocket.app.state.matching_service
    interval_seconds = websocket.app.state.websocket_push_interval_seconds

    try:
        while True:
            opportunities = await matching_service.find_opportunities(cache)
            await websocket.send_json([OpportunityService.serialize(item) for item in opportunities])
            await asyncio.sleep(interval_seconds)
    except WebSocketDisconnect:
        return
