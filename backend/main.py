import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.api.routes import router
from backend.api.websocket import router as websocket_router
from backend.collectors.kalshi import KalshiCollector
from backend.collectors.polymarket import PolymarketCollector
from backend.config import settings
from backend.services.market_cache import MarketCache
from backend.services.market_discovery import MarketDiscoveryService
from backend.services.matching_service import MatchingService
from backend.services.opportunity_broadcaster import OpportunityBroadcaster

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)


def create_app(
    start_collectors: bool | None = None,
    kalshi_collector: KalshiCollector | None = None,
    polymarket_collector: PolymarketCollector | None = None,
) -> FastAPI:
    collectors_enabled = settings.enable_live_collectors if start_collectors is None else start_collectors

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        cache = MarketCache()
        kalshi = kalshi_collector or KalshiCollector(
            base_url=settings.kalshi_base_url,
            timeout=settings.collector_timeout_seconds,
            max_pages=settings.collector_max_pages,
        )
        polymarket = polymarket_collector or PolymarketCollector(
            base_url=settings.polymarket_base_url,
            timeout=settings.collector_timeout_seconds,
            max_pages=settings.collector_max_pages,
        )
        matching_service = MatchingService(
            kalshi_collector=kalshi,
            polymarket_collector=polymarket,
            match_confidence_threshold=settings.minimum_match_confidence,
            stale_after_seconds=settings.stale_after_seconds,
        )
        discovery = MarketDiscoveryService(
            cache=cache,
            collectors=[kalshi, polymarket],
            refresh_seconds=settings.market_refresh_seconds,
        )
        broadcaster = OpportunityBroadcaster(
            cache=cache,
            matching_service=matching_service,
            interval_seconds=settings.websocket_push_interval_seconds,
        )
        app.state.market_cache = cache
        app.state.market_discovery = discovery
        app.state.matching_service = matching_service
        app.state.opportunity_broadcaster = broadcaster
        logger.info("Starting scanner: live_collectors=%s", collectors_enabled)
        broadcaster.start()
        if collectors_enabled:
            discovery.start()
        yield
        logger.info("Shutting down scanner")
        await discovery.stop()
        await broadcaster.stop()

    app = FastAPI(
        title="Kalshi Polymarket Sports Arbitrage Scanner",
        lifespan=lifespan,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[settings.allowed_origin],
        allow_credentials=False,
        allow_methods=["GET"],
        allow_headers=["*"],
    )
    app.include_router(router)
    app.include_router(websocket_router)
    return app


app = create_app()
