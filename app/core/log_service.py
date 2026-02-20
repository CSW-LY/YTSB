"""Async log writing service for background task processing."""

import asyncio
import logging
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.database import IntentRecognitionLog

logger = logging.getLogger(__name__)


class AsyncLogService:
    """Service for async background log writing."""

    def __init__(self):
        self._queue: asyncio.Queue = asyncio.Queue()
        self._worker_task: Optional[asyncio.Task] = None
        self._running = False

    async def start(self) -> None:
        """Start the background log worker."""
        if self._running:
            return

        self._running = True
        self._worker_task = asyncio.create_task(self._worker())
        logger.info("Async log service started")

    async def stop(self) -> None:
        """Stop the background log worker."""
        self._running = False
        if self._worker_task:
            await self._worker_task
        logger.info("Async log service stopped")

    async def _worker(self) -> None:
        """Background worker that processes log queue."""
        global _session_maker

        while self._running:
            try:
                log_entry = await asyncio.wait_for(
                    self._queue.get(),
                    timeout=1.0
                )

                if log_entry is None:
                    continue

                async with _session_maker() as session:
                    session.add(log_entry)
                    await session.commit()
                    logger.debug(f"Log entry saved: {log_entry.app_key}")

            except asyncio.TimeoutError:
                continue
            except Exception as e:
                logger.error(f"Error saving log entry: {e}")

    async def enqueue_log(self, log_entry: IntentRecognitionLog) -> None:
        """Enqueue a log entry for background processing."""
        try:
            self._queue.put_nowait(log_entry)
        except Exception as e:
            logger.error(f"Failed to enqueue log: {e}")

    async def enqueue_logs(self, log_entries: list[IntentRecognitionLog]) -> None:
        """Enqueue multiple log entries for background processing."""
        for log_entry in log_entries:
            await self.enqueue_log(log_entry)


# Global async log service instance
_async_log_service: Optional[AsyncLogService] = None
_session_maker = None


def get_async_log_service() -> AsyncLogService:
    """Get or create async log service singleton."""
    global _async_log_service
    if _async_log_service is None:
        _async_log_service = AsyncLogService()
    return _async_log_service


def set_session_maker(session_maker):
    """Set the session maker for async log service."""
    global _session_maker
    _session_maker = session_maker
