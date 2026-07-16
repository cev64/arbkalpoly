from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from backend.services.opportunity_broadcaster import OpportunityBroadcaster
from backend.services.opportunity_service import OpportunityService

router = APIRouter()


@router.websocket("/ws/opportunities")
async def stream_opportunities(websocket: WebSocket) -> None:
    await websocket.accept()
    broadcaster: OpportunityBroadcaster = websocket.app.state.opportunity_broadcaster
    queue = broadcaster.subscribe()
    try:
        while True:
            opportunities = await queue.get()
            await websocket.send_json([OpportunityService.serialize(item) for item in opportunities])
    except WebSocketDisconnect:
        pass
    finally:
        broadcaster.unsubscribe(queue)
