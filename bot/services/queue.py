# bot/services/queue.py
"""Queue management for download tasks."""

import asyncio
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from loguru import logger

from bot.config import config
from bot.utils.exceptions import QueueFullError

# Type hint for Task
Task = asyncio.Task


@dataclass
class DownloadTask:
    """Represents a download task in the queue."""

    chat_id: int
    url: str
    format_string: str
    status_message_id: Optional[int] = None
    additional_data: Optional[Dict[str, Any]] = None


class DownloadQueue:
    """Manages a queue of download tasks."""

    def __init__(self) -> None:
        """Initialize download queue."""
        self.queue: asyncio.Queue[DownloadTask] = asyncio.Queue()
        self.is_processing = False
        self.current_task: Optional[DownloadTask] = None
        self._worker_task: Optional[Task[None]] = None
        self._lock = asyncio.Lock()
        self._queue_items: List[DownloadTask] = []  # Track queue items safely

    async def add_task(self, task: DownloadTask) -> int:
        """
        Add a task to the queue.

        Args:
            task: Download task to add

        Returns:
            Current queue size after adding the task

        Raises:
            QueueFullError: If queue is full or user has too many tasks
        """
        async with self._lock:
            # Check global queue limit
            if len(self._queue_items) >= config.MAX_QUEUE_SIZE:
                raise QueueFullError(
                    f"Queue is full (maximum {config.MAX_QUEUE_SIZE} tasks)",
                    context={"queue_size": len(self._queue_items), "limit": config.MAX_QUEUE_SIZE},
                )

            # Check per-user limit
            user_task_count = sum(1 for t in self._queue_items if t.chat_id == task.chat_id)
            if user_task_count >= config.MAX_USER_TASKS:
                raise QueueFullError(
                    f"Too many tasks for user (maximum {config.MAX_USER_TASKS} per user)",
                    context={"user_id": task.chat_id, "user_tasks": user_task_count, "limit": config.MAX_USER_TASKS},
                )

            await self.queue.put(task)
            self._queue_items.append(task)
            queue_size = len(self._queue_items)

        url = task.url
        format_str = task.format_string
        logger.info(
            f"Task added to queue: {url}, format: {format_str}, position: {queue_size}",
            extra={"user_id": task.chat_id, "queue_size": queue_size},
        )

        # Start worker if not already running
        if self._worker_task is None or self._worker_task.done():
            self._worker_task = asyncio.create_task(self._process_queue())

        return queue_size

    def get_queue_position(self, chat_id: int, url: str) -> Optional[int]:
        """
        Get position of a task in the queue.

        Args:
            chat_id: User chat ID
            url: URL being downloaded

        Returns:
            Position in queue (1-based) or None if not found
        """
        if not self._queue_items:
            return None

        return next(
            (i + 1 for i, task in enumerate(self._queue_items) if task.chat_id == chat_id and task.url == url), None
        )

    def is_user_in_queue(self, chat_id: int) -> bool:
        """
        Check if user has tasks in queue.

        Args:
            chat_id: User chat ID

        Returns:
            True if user has tasks in queue, False otherwise
        """
        return any(task.chat_id == chat_id for task in self._queue_items)

    async def clear_user_tasks(self, chat_id: int) -> int:
        """
        Remove all tasks for a specific user.

        Args:
            chat_id: User chat ID

        Returns:
            Number of tasks removed
        """
        async with self._lock:
            if not self._queue_items:
                return 0

            # Create a new queue without the specified user's tasks
            new_queue: asyncio.Queue[DownloadTask] = asyncio.Queue()
            new_queue_items = []
            removed_count = 0

            for task in self._queue_items:
                if task.chat_id == chat_id:
                    removed_count += 1
                else:
                    await new_queue.put(task)
                    new_queue_items.append(task)

            self.queue = new_queue
            self._queue_items = new_queue_items
            logger.info(f"Removed {removed_count} tasks for chat_id: {chat_id}")
            return removed_count

    async def _process_queue(self) -> None:
        """Process tasks in the queue sequentially."""
        while not self.queue.empty():
            self.is_processing = True
            self.current_task = await self.queue.get()

            # Remove from tracking list
            async with self._lock:
                if self.current_task in self._queue_items:
                    self._queue_items.remove(self.current_task)

            try:
                await self._process_single_task()
            except Exception as e:
                task_url = self.current_task.url if self.current_task else "unknown"
                logger.error(f"Error processing task {task_url}: {str(e)}", exc_info=True)
            finally:
                self.queue.task_done()
                self.current_task = None

        self.is_processing = False

    async def _process_single_task(self) -> None:
        """Process a single task from the queue."""
        if not self.current_task:
            return

        task_url = self.current_task.url
        format_str = self.current_task.format_string
        logger.info(f"Processing task: {task_url}, format: {format_str}")

        bot = self._get_bot_instance()
        if not bot:
            return

        # Import here to avoid circular imports
        from bot.services.downloader import download_youtube_video

        await download_youtube_video(
            bot,
            self.current_task.chat_id,
            self.current_task.url,
            self.current_task.format_string,
        )

        logger.info(f"Task completed: {task_url}")

    def _get_bot_instance(self) -> Optional[Any]:
        """Get bot instance from task data."""
        if not self.current_task:
            return None

        additional_data = self.current_task.additional_data or {}
        bot = additional_data.get("bot")
        if not bot:
            logger.error("Bot instance not provided in task data")
        return bot


# Global queue instance
download_queue = DownloadQueue()
