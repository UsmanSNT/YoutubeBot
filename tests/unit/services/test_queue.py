# tests/test_queue.py
"""Tests for download queue."""

import pytest

from bot.services.queue import DownloadQueue, DownloadTask


@pytest.mark.asyncio
async def test_queue_add_task(mocker):
    """Test adding tasks to the queue."""
    queue = DownloadQueue()

    # Mock _process_queue to prevent actual execution
    queue._process_queue = mocker.AsyncMock()
    # Add a task
    task = DownloadTask(chat_id=123, url="https://example.com", format_string="test_format")
    position = await queue.add_task(task)

    # Should be first in queue
    assert position == 1
    assert queue.is_user_in_queue(123)
    assert not queue.is_user_in_queue(456)
    # Add another task
    task2 = DownloadTask(chat_id=456, url="https://example2.com", format_string="test_format")
    position = await queue.add_task(task2)

    # Should be second in queue
    assert position == 2
    assert queue.is_user_in_queue(123)
    assert queue.is_user_in_queue(456)


@pytest.mark.asyncio
async def test_queue_processing(mocker):
    """Test queue processing."""
    queue = DownloadQueue()

    # Create mock bot
    mock_bot = mocker.AsyncMock()

    # Mock download function
    mock_download = mocker.patch("bot.services.downloader.download_youtube_video", mocker.AsyncMock())

    # Add tasks
    task1 = DownloadTask(
        chat_id=123,
        url="https://example.com/1",
        format_string="test_format",
        additional_data={"bot": mock_bot},
    )

    task2 = DownloadTask(
        chat_id=456,
        url="https://example.com/2",
        format_string="test_format",
        additional_data={"bot": mock_bot},
    )

    await queue.add_task(task1)
    await queue.add_task(task2)

    # Process the queue
    await queue._process_queue()

    # Both tasks should have been processed
    assert mock_download.call_count == 2

    # Queue should be empty
    assert queue.queue.empty()
    assert not queue.is_processing


@pytest.mark.asyncio
async def test_queue_error_handling(mocker):
    """Test queue handles errors properly."""
    queue = DownloadQueue()

    # Create mock bot
    mock_bot = mocker.AsyncMock()

    # Mock download function to raise an exception
    mock_download = mocker.patch(
        "bot.services.downloader.download_youtube_video",
        mocker.AsyncMock(side_effect=Exception("Test error")),
    )
    mock_logger_error = mocker.patch("bot.services.queue.logger.error", mocker.MagicMock())

    # Add a task
    task = DownloadTask(
        chat_id=123,
        url="https://example.com",
        format_string="test_format",
        additional_data={"bot": mock_bot},
    )

    await queue.add_task(task)

    # Process the queue
    await queue._process_queue()

    # Function should have been called
    mock_download.assert_called_once()

    # Error should have been logged
    mock_logger_error.assert_called_once()

    # Queue should be empty despite the error
    assert queue.queue.empty()
    assert not queue.is_processing


@pytest.mark.asyncio
async def test_clear_user_tasks():
    """Test clearing user tasks from queue."""
    queue = DownloadQueue()

    # Add tasks for two different users
    task1 = DownloadTask(chat_id=123, url="https://example.com/1", format_string="test_format")
    task2 = DownloadTask(chat_id=123, url="https://example.com/2", format_string="test_format")
    task3 = DownloadTask(chat_id=456, url="https://example.com/3", format_string="test_format")

    # Add tasks to queue using proper method
    await queue.add_task(task1)
    await queue.add_task(task2)
    await queue.add_task(task3)
    # Clear tasks for user 123
    removed = await queue.clear_user_tasks(123)

    # Should have removed 2 tasks
    assert removed == 2

    # Queue should have 1 task remaining
    assert queue.queue.qsize() == 1
    assert not queue.is_user_in_queue(123)
    assert queue.is_user_in_queue(456)


@pytest.mark.asyncio
async def test_clear_user_tasks_empty_queue():
    """Test clearing user tasks from an empty queue."""
    queue = DownloadQueue()

    # Clear tasks for non-existent user
    removed = await queue.clear_user_tasks(123)

    # Should have removed 0 tasks
    assert removed == 0
    assert queue.queue.empty()


@pytest.mark.asyncio
async def test_get_queue_position():
    """Test get_queue_position method."""
    queue = DownloadQueue()

    # Add tasks for different users
    task1 = DownloadTask(chat_id=123, url="https://example.com/1", format_string="test_format")
    task2 = DownloadTask(chat_id=456, url="https://example.com/2", format_string="test_format")
    task3 = DownloadTask(chat_id=123, url="https://example.com/3", format_string="test_format")

    # Add tasks to queue using proper method
    await queue.add_task(task1)
    await queue.add_task(task2)
    await queue.add_task(task3)

    # Check positions
    assert queue.get_queue_position(123, "https://example.com/1") == 1
    assert queue.get_queue_position(456, "https://example.com/2") == 2
    assert queue.get_queue_position(123, "https://example.com/3") == 3
    assert queue.get_queue_position(789, "https://example.com/4") is None


@pytest.mark.asyncio
async def test_get_queue_position_empty_queue():
    """Test get_queue_position with empty queue."""
    queue = DownloadQueue()
    assert queue.get_queue_position(123, "https://example.com") is None


@pytest.mark.asyncio
async def test_process_queue_missing_bot(mocker):
    """Test queue processing when bot is missing in task data."""
    queue = DownloadQueue()

    # Mock logger
    mock_logger_error = mocker.patch("bot.services.queue.logger.error")

    # Add task without bot
    task = DownloadTask(
        chat_id=123,
        url="https://example.com",
        format_string="test_format",
        additional_data={},  # No bot instance
    )

    # Add directly to queue
    queue.queue.put_nowait(task)

    # Process the queue
    await queue._process_queue()

    # Should log error about missing bot
    mock_logger_error.assert_called_once()
    assert "Bot instance not provided" in mock_logger_error.call_args[0][0]

    # Queue should be empty
    assert queue.queue.empty()
    assert not queue.is_processing
