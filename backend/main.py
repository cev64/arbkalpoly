from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.api.routes import router
from backend.collectors.kalshi import KalshiCollector
from backend.collectors.polymarket import PolymarketCollector
from backend.config import settings
from backend.services.market_cache import MarketCache
from backend.services.market_discovery import MarketDiscoveryService


def create_app(start_collectors: bool | None = None) -> FastAPI:
    collectors_enabled = settings.enable_live_collectors if start_collectors is None else start_collectors

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        cache = MarketCache()
        discovery = MarketDiscoveryService(
            cache=cache,
            collectors=[
                KalshiCollector(
                    base_url=settings.kalshi_base_url,
                    timeout=settings.collector_timeout_seconds,
                    max_pages=settings.collector_max_pages,
                ),
                PolymarketCollector(
                    base_url=settings.polymarket_base_url,
                    timeout=settings.collector_timeout_seconds,
                    max_pages=settings.collector_max_pages,
                ),
            ],
            refresh_seconds=settings.market_refresh_seconds,
        )
        app.state.market_cache = cache
        app.state.market_discovery = discovery
        if collectors_enabled:
            discovery.start()
        yield
        await discovery.stop()

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
    return app


app = create_app()
