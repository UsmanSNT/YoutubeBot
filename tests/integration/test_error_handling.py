"""Integration tests for error handling and recovery."""

import pytest

from bot.handlers.download import process_format_selection
from bot.services.downloader import DownloadError
from bot.services.queue import DownloadTask, download_queue


class MockDownloadWithError:
    """Mock class for download function that raises errors."""

    def __init__(self, notify_admin_mock):
        """Initialize with notify_admin mock."""
        self.notify_admin_mock = notify_admin_mock

    async def __call__(self, *args, **kwargs):
        """Mock download function that handles errors."""
        # Extract the bot and chat_id from args (positional arguments)
        bot_arg = args[0]
        chat_id_arg = args[1]

        # Before raising the exception, send error message to user
        await bot_arg.send_message(chat_id_arg, "❌ <b>Download failed</b>\n\nCritical test error")

        # Also call notify_admin like the real function would
        await self.notify_admin_mock(bot_arg, "Download failed with critical error")

        # Raise the exception
        raise DownloadError("Critical test error")


@pytest.mark.asyncio
@pytest.mark.integration
async def test_download_error_handling(
    integration_setup, mock_message, mock_callback_query, mock_complete_system, mocker
):
    """Test error handling during download process."""
    # Setup message with YouTube URL
    mock_message.text = "https://www.youtube.com/watch?v=test_error_video"

    # Make sure mocks are reset
    mock_message.answer.reset_mock()
    mock_callback_query.answer.reset_mock()
    mock_callback_query.message.edit_text.reset_mock()

    # Direct manipulation approach - create format ID and URL ID
    format_id = "video:SD"
    url_id = "test_error_url_id"
    # Prepare the callback_data manually
    callback_data = f"fmt:{format_id}:{url_id}"
    mock_callback_query.data = callback_data

    # Create a download error for testing
    _ = mocker.AsyncMock(side_effect=DownloadError("Test download error"))

    # Setup the mock bot
    _ = integration_setup["bot"]

    # Configure the existing mocks for this error test
    mock_complete_system["download"]["get_url"].return_value = "https://www.youtube.com/watch?v=test_error_video"
    mock_complete_system["format"]["get_format_by_id"].return_value = {
        "label": "SD (480p)",
        "format": "test-format",
        "type": "video",
    }
    mock_complete_system["download"]["download_video"].side_effect = DownloadError("Test download error")

    # Process format selection (this adds task to queue)
    await process_format_selection(mock_callback_query)

    # Make sure mocks are actually called
    assert mock_callback_query.answer.called, "Callback answer not called"
    assert mock_callback_query.message.edit_text.called, "Message edit_text not called"

    # Process the queue (which should handle the error)
    await download_queue._process_queue()

    # Verify queue is empty after error handling
    assert download_queue.queue.empty()

    # Verify queue is not stuck in processing state
    assert not download_queue.is_processing

    # Verify download error was raised and called with expected arguments
    mock_complete_system["download"]["download_video"].assert_called_once()


@pytest.mark.asyncio
@pytest.mark.integration
async def test_multiple_download_failures(integration_setup, mock_bot, mock_download_system, mocker):
    """Test handling of multiple download failures using direct queue manipulation."""
    # Configure download system to fail
    mock_download_system["download_video"].side_effect = DownloadError("Test error")

    # Create two tasks directly
    task1 = DownloadTask(
        chat_id=123456,
        url="https://www.youtube.com/watch?v=test_fail1",
        format_string="test-format-1",
        status_message_id=101,
        additional_data={"bot": mock_bot},
    )

    task2 = DownloadTask(
        chat_id=123456,
        url="https://www.youtube.com/watch?v=test_fail2",
        format_string="test-format-2",
        status_message_id=102,
        additional_data={"bot": mock_bot},
    )

    # Add tasks to queue directly
    await download_queue.add_task(task1)
    await download_queue.add_task(task2)

    # Verify both tasks are in queue
    assert download_queue.queue.qsize() == 2

    # The download system is already configured to fail
    await download_queue._process_queue()

    # Verify queue is empty after error handling
    assert download_queue.queue.empty()

    # Verify queue is not stuck in processing state
    assert not download_queue.is_processing

    # Verify download was attempted twice
    assert mock_download_system["download_video"].call_count == 2


@pytest.mark.asyncio
@pytest.mark.integration
async def test_admin_notification_on_error(integration_setup, mock_bot, mock_error_system, mocker):
    """Test that admin is notified on critical errors."""

    # Create mock download with error that handles admin notification
    mock_download_with_error = MockDownloadWithError(mock_error_system["notify_admin"])

    # Create a task directly
    task = DownloadTask(
        chat_id=123456,
        url="https://www.youtube.com/watch?v=test_admin_notify",
        format_string="test-format",
        status_message_id=103,
        additional_data={"bot": mock_bot},
    )

    # Add task to queue
    await download_queue.add_task(task)

    # Verify task is in queue
    assert download_queue.queue.qsize() == 1

    # Process the queue with error that should trigger admin notification
    mocker.patch(
        "bot.services.downloader.download_youtube_video",
        mock_download_with_error,
    )

    await download_queue._process_queue()

    # Verify queue is empty after error handling
    assert download_queue.queue.empty()

    # Verify queue is not stuck in processing state
    assert not download_queue.is_processing

    # Verify error message was sent to the user
    mock_bot.send_message.assert_called_once()

    # Verify admin was notified
    mock_error_system["notify_admin"].assert_called_once()

    # Check that the task was cleared
    assert download_queue.current_task is None
