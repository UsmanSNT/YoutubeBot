"""Integration tests for the download workflow."""

import pytest
from aiogram.types import InlineKeyboardMarkup

from bot.handlers.download import process_format_selection, process_url
from bot.services.queue import DownloadTask, download_queue


@pytest.mark.asyncio
@pytest.mark.integration
async def test_full_download_workflow(integration_setup, mock_message, mock_callback_query, mock_complete_system):
    """Test the full download workflow from URL to completed download."""
    # Setup message with YouTube URL
    mock_message.text = "https://www.youtube.com/watch?v=test_video"
    # Process URL
    await process_url(mock_message)

    # Verify format selection keyboard was sent
    mock_message.answer.assert_called_once()
    args, kwargs = mock_message.answer.call_args
    assert "Choose Download Format" in args[0]
    assert "reply_markup" in kwargs

    # Extract the keyboard and verify options
    markup = kwargs["reply_markup"]
    assert isinstance(markup, InlineKeyboardMarkup)
    assert len(markup.inline_keyboard) > 0

    # Simulate user selecting a format (e.g., HD)
    first_button = markup.inline_keyboard[0][0]
    callback_data = first_button.callback_data
    assert callback_data.startswith("fmt:")

    # Setup callback query with the selected format
    mock_callback_query.data = callback_data

    # Use the mocked get_url from the fixture
    # Process format selection
    await process_format_selection(mock_callback_query)

    # Verify callback was answered
    mock_callback_query.answer.assert_called_once()

    # Verify message was edited to show download status
    mock_callback_query.message.edit_text.assert_called_once()
    edit_call_args = mock_callback_query.message.edit_text.call_args
    edit_args = edit_call_args[0][0]
    assert "Download" in edit_args

    # Verify task was added to queue
    assert not download_queue.queue.empty()

    # Process the download queue manually since we're in test mode

    # Download task processing is already mocked by the fixture
    await download_queue._process_queue()

    # Verify queue is now empty (task was processed)
    assert download_queue.queue.empty()

    # In real scenario, the bot would have sent a document
    # Since we mocked the download function, we just verify
    # that the queue processing completed successfully
    assert not download_queue.is_processing


@pytest.mark.asyncio
@pytest.mark.integration
async def test_download_workflow_with_queue(
    integration_setup, mock_message, mock_callback_query, mock_complete_system, mocker
):
    """Test multiple downloads being queued and processed in order."""
    # This test verifies that multiple downloads can be processed sequentially
    # Start with empty queue
    assert download_queue.queue.empty()

    # Use mock bot instance to avoid real API calls
    mock_bot = integration_setup["bot"]
    mock_bot.edit_message_text = mocker.AsyncMock()

    # Add first task to queue (directly, bypassing process_format_selection)
    task1 = DownloadTask(
        chat_id=123456,
        url="https://www.youtube.com/watch?v=test_video1",
        format_string="best[height<=720]",
        status_message_id=100,
        additional_data={"bot": mock_bot},
    )

    # Add second task
    task2 = DownloadTask(
        chat_id=123456,
        url="https://www.youtube.com/watch?v=test_video2",
        format_string="best[height<=720]",
        status_message_id=101,
        additional_data={"bot": mock_bot},
    )

    # Add tasks to queue
    position1 = await download_queue.add_task(task1)
    position2 = await download_queue.add_task(task2)

    # Verify queue positions
    assert position1 == 1
    assert position2 == 2

    # Verify queue size
    assert download_queue.queue.qsize() == 2

    # Process tasks
    await download_queue._process_queue()

    # Verify queue is now empty (both tasks were processed)
    assert download_queue.queue.empty()


@pytest.mark.asyncio
@pytest.mark.integration
async def test_download_workflow_non_youtube_url(integration_setup, mock_message, mock_download_system, mocker):
    """Test handling of non-YouTube URLs."""
    # Setup message with non-YouTube URL
    mock_message.text = "https://example.com/video"

    # Override is_youtube_url to return False for this test
    mock_download_system["is_youtube_url"].return_value = False
    # Process URL
    await process_url(mock_message)

    # Verify error message was sent
    mock_message.answer.assert_called_once()
    args = mock_message.answer.call_args[0][0]
    assert "Unsupported URL" in args
    assert "valid YouTube link" in args

    # Verify no tasks were added to queue
    assert download_queue.queue.empty()


@pytest.mark.asyncio
@pytest.mark.integration
async def test_download_workflow_unauthorized_user(integration_setup, mock_message, unauthorized_user):
    """Test download workflow with unauthorized user."""
    # Setup message with unauthorized user
    mock_message.from_user = unauthorized_user
    mock_message.chat.id = unauthorized_user.id
    mock_message.text = "https://www.youtube.com/watch?v=test_video"

    # Process URL
    await process_url(mock_message)

    # Verify access denied message was sent
    mock_message.answer.assert_called_once()
    args = mock_message.answer.call_args[0][0]
    assert "Access Denied" in args

    # Verify no tasks were added to queue
    assert download_queue.queue.empty()


@pytest.mark.asyncio
@pytest.mark.integration
async def test_queue_notification_message(
    integration_setup, mock_message, mock_callback_query, mock_complete_system, mocker
):
    """Test notification messages for queued downloads."""
    # Setup message with YouTube URL
    mock_message.text = "https://www.youtube.com/watch?v=test_video_queued"

    # Update store_url mock to return specific ID for this test
    mock_complete_system["download"]["store_url"].return_value = "test_queue_url_id"
    # Process URL
    await process_url(mock_message)

    # Extract the keyboard and verify options
    _, kwargs = mock_message.answer.call_args
    markup = kwargs["reply_markup"]
    callback_data = markup.inline_keyboard[0][0].callback_data

    # Setup callback query with the format data
    mock_callback_query.data = callback_data
    # Mock bot is included in integration setup
    _ = integration_setup["bot"]

    # Set up mocks to simulate active queue processing
    mock_complete_system["download"]["get_url"].return_value = "https://www.youtube.com/watch?v=test_video_queued"
    # Force download_queue.is_processing to return True
    mocker.patch("bot.services.queue.download_queue.is_processing", True)
    # Force is_user_in_queue to return False to test notification message
    mocker.patch(
        "bot.services.queue.download_queue.is_user_in_queue",
        return_value=False,
    )

    # Process format selection
    await process_format_selection(mock_callback_query)

    # Verify callback was answered
    mock_callback_query.answer.assert_called_once()

    # Verify message was edited with the notification about queuing
    edit_call_args = mock_callback_query.message.edit_text.call_args
    edit_text_args = edit_call_args[0][0]
    assert "queued" in edit_text_args
    assert "notified when processing begins" in edit_text_args
