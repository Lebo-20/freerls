import asyncio
from dataclasses import dataclass, field
from typing import Any, Optional

@dataclass(order=True)
class DramaTask:
    priority: int
    drama_id: str = field(compare=False)
    title: Optional[str] = field(default=None, compare=False)
    event: Any = field(default=None, compare=False)

class TaskQueue:
    def __init__(self):
        self._queue = asyncio.PriorityQueue()
        self._processing = set()
        self._enqueued = set()

    async def put(self, task: DramaTask):
        if task.drama_id in self._enqueued: return
        self._enqueued.add(task.drama_id)
        await self._queue.put(task)

    async def get(self) -> DramaTask:
        task = await self._queue.get()
        self._enqueued.discard(task.drama_id)
        return task

    def task_done(self):
        self._queue.task_done()

    def is_processing(self, drama_id):
        return drama_id in self._processing

    def is_queued(self, drama_id):
        return drama_id in self._enqueued

    def add_processing(self, drama_id):
        self._processing.add(drama_id)

    def remove_processing(self, drama_id):
        self._processing.discard(drama_id)

    def qsize(self):
        return self._queue.qsize()

    def processing_count(self):
        return len(self._processing)
