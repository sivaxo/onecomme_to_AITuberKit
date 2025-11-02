"""Priority queue manager for comment processing."""
from __future__ import annotations

import asyncio
import heapq
import time
from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass(order=True)
class QueueItem:
    """Represents an item waiting to be processed."""

    priority: int
    inserted_at: float = field(init=False, repr=False)
    comment_id: str = field(compare=False)
    comment_data: dict[str, Any] = field(compare=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, "inserted_at", time.time())


class QueueManager:
    """Thread-safe priority queue supporting optional single-processing mode."""

    def __init__(self, max_size: int, allow_concurrent: bool) -> None:
        self._max_size = max_size
        self._allow_concurrent = allow_concurrent
        self._items: list[tuple[int, float, QueueItem]] = []
        self._lock = asyncio.Lock()
        self._is_processing = False

    async def enqueue(self, item: QueueItem) -> Optional[QueueItem]:
        """Insert item into queue, returning evicted item if overflow occurs."""

        async with self._lock:
            heapq.heappush(self._items, (item.priority, item.inserted_at, item))
            evicted: Optional[QueueItem] = None
            if self._max_size > 0 and len(self._items) > self._max_size:
                # remove the item with the lowest priority (i.e., highest numeric value)
                evicted = max(self._items, key=lambda candidate: candidate[0])[2]
                self._items.remove((evicted.priority, evicted.inserted_at, evicted))
                heapq.heapify(self._items)
            return evicted

    async def dequeue(self) -> Optional[QueueItem]:
        """Retrieve next item respecting concurrency configuration."""

        async with self._lock:
            if not self._items:
                return None
            if self._is_processing and not self._allow_concurrent:
                return None

            _, _, item = heapq.heappop(self._items)
            if not self._allow_concurrent:
                self._is_processing = True
            return item

    async def mark_idle(self) -> None:
        """Mark queue as having no active processing item."""

        async with self._lock:
            self._is_processing = False

    async def clear(self) -> None:
        async with self._lock:
            self._items.clear()
            self._is_processing = False

    async def size(self) -> int:
        async with self._lock:
            return len(self._items)
