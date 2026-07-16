import asyncio
from datetime import UTC, datetime
from typing import Protocol

from backend.models.market import NormalizedMarket
from backend.services.market_cache import MarketCache


class MarketCollector(Protocol):
    exchange: str

    async def fetch_markets(self) -> list[NormalizedMarket]: ...


class MarketDiscoveryService:
    def __init__(
        self,
        cache: MarketCache,
        collectors: list[MarketCollector],
        refresh_seconds: int = 300,
    ) -> None:
        self.cache = cache
        self.collectors = collectors
        self.refresh_seconds = refresh_seconds
        self.last_attempt: datetime | None = None
        self.last_success: datetime | None = None
        self.errors: dict[str, str] = {}
        self._task: asyncio.Task | None = None
        self._stop = asyncio.Event()

    async def refresh(self) -> int:
        self.last_attempt = datetime.now(UTC)
        results = await asyncio.gather(
            *(collector.fetch_markets() for collector in self.collectors),
            return_exceptions=True,
        )

        refreshed = 0
        errors: dict[str, str] = {}
        for collector, result in zip(self.collectors, results):
            if isinstance(result, BaseException):
                errors[collector.exchange] = f"{type(result).__name__}: {result}"
                continue
            self.cache.replace_exchange(collector.exchange, result)
            refreshed += len(result)

        self.errors = errors
        if len(errors) < len(self.collectors):
            self.last_success = datetime.now(UTC)
        return refreshed

    def start(self) -> None:
        if self._task is None or self._task.done():
            self._stop.clear()
            self._task = asyncio.create_task(self._run(), name="market-discovery")

    async def stop(self) -> None:
        self._stop.set()
        if self._task is not None:
            await self._task
            self._task = None

    async def _run(self) -> None:
        while not self._stop.is_set():
            await self.refresh()
            try:
                await asyncio.wait_for(self._stop.wait(), timeout=self.refresh_seconds)
            except TimeoutError:
                continue

    def status(self) -> dict:
        return {
            "last_attempt": self.last_attempt.isoformat() if self.last_attempt else None,
            "last_success": self.last_success.isoformat() if self.last_success else None,
            "errors": self.errors,
            "running": self._task is not None and not self._task.done(),
        }
