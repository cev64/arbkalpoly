import asyncio

from backend.models.opportunity import Opportunity
from backend.services.market_cache import MarketCache
from backend.services.matching_service import MatchingService


class OpportunityBroadcaster:
    """Computes opportunities once per interval and fans the result out to every subscriber.

    Without this, each connected WebSocket client would independently poll the live
    exchange order-book APIs on its own loop, multiplying real network load by the
    number of connected clients.
    """

    def __init__(self, cache: MarketCache, matching_service: MatchingService, interval_seconds: float) -> None:
        self.cache = cache
        self.matching_service = matching_service
        self.interval_seconds = interval_seconds
        self.latest: list[Opportunity] = []
        self._subscribers: set[asyncio.Queue] = set()
        self._task: asyncio.Task | None = None
        self._stop = asyncio.Event()

    def subscribe(self) -> asyncio.Queue:
        queue: asyncio.Queue = asyncio.Queue(maxsize=1)
        queue.put_nowait(self.latest)
        self._subscribers.add(queue)
        return queue

    def unsubscribe(self, queue: asyncio.Queue) -> None:
        self._subscribers.discard(queue)

    async def refresh_once(self) -> list[Opportunity]:
        self.latest = await self.matching_service.find_opportunities(self.cache)
        for queue in list(self._subscribers):
            if queue.full():
                queue.get_nowait()
            queue.put_nowait(self.latest)
        return self.latest

    def start(self) -> None:
        if self._task is None or self._task.done():
            self._stop.clear()
            self._task = asyncio.create_task(self._run(), name="opportunity-broadcaster")

    async def stop(self) -> None:
        self._stop.set()
        if self._task is not None:
            await self._task
            self._task = None

    async def _run(self) -> None:
        while not self._stop.is_set():
            await self.refresh_once()
            try:
                await asyncio.wait_for(self._stop.wait(), timeout=self.interval_seconds)
            except TimeoutError:
                continue
