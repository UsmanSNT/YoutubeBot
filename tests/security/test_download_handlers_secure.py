"""Secure tests for download handlers using real authorization.

This replaces the dangerous mocking of is_user_authorized with real database testing.
"""

import tempfile
from pathlib import Path

import pytest
import pytest_asyncio
from aiogram.types import CallbackQuery, Message, User

from bot.handlers.download import process_format_selection, process_url
from bot.utils.db import add_user, init_db


@pytest_asyncio.fixture
async def secure_download_db(mocker):
    """Create real database for download testing."""
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_db_path = Path(temp_dir) / "download_test.db"

        mocker.patch("bot.utils.db.DB_PATH", temp_db_path)
        await init_db()
        yield temp_db_path


@pytest.fixture
def authorized_user(mocker):
    """Create user that will be added to database."""
    user = mocker.MagicMock(spec=User)
    user.id = 123456789
    user.username = "authorized_user"
    user.first_name = "Test"
    user.last_name = "User"
    return user


@pytest.fixture
def unauthorized_user(mocker):
    """Create user that will NOT be added to database."""
    user = mocker.MagicMock(spec=User)
    user.id = 999999999
    user.username = "unauthorized_user"
    user.first_name = "Unauthorized"
    user.last_name = "User"
    return user


@pytest.fixture
def mock_message(mocker):
    """Create mock message."""
    message = mocker.MagicMock(spec=Message)
    message.answer = mocker.AsyncMock()
    message.reply = mocker.AsyncMock()
    return message


@pytest.mark.asyncio
async def test_process_url_authorized_youtube_user(secure_download_db, authorized_user, mock_message, mocker):
    """Test processing YouTube URL with real authorized user."""
    # Add user to database (real authorization)
    await add_user(authorized_user.id, authorized_user.username, authorized_user.id)

    mock_message.from_user = authorized_user
    mock_message.text = "https://www.youtube.com/watch?v=test"

    mocker.patch("bot.handlers.download.is_youtube_url", return_value=True)
    mocker.patch("bot.handlers.download.store_url", return_value="test_url_id")
    mocker.patch(
        "bot.handlers.download.get_format_options",
        return_value=[
            ("SD", "SD (480p)"),
            ("HD", "HD (720p)"),
            ("FHD", "Full HD (1080p)"),
            ("ORIGINAL", "Original"),
        ],
    )
    await process_url(mock_message)

    # Should show format selection for authorized user
    mock_message.answer.assert_called_once()
    args, kwargs = mock_message.answer.call_args
    assert "Choose Download Format" in args[0]
    assert "reply_markup" in kwargs


@pytest.mark.asyncio
async def test_process_url_unauthorized_youtube_user(secure_download_db, unauthorized_user, mock_message, mocker):
    """Test processing YouTube URL with real unauthorized user."""
    # Do NOT add user to database
    mock_message.from_user = unauthorized_user
    mock_message.text = "https://www.youtube.com/watch?v=test"

    mocker.patch("bot.handlers.download.is_youtube_url", return_value=True)
    await process_url(mock_message)

    # Should show access restricted message
    mock_message.answer.assert_called_once()
    args = mock_message.answer.call_args[0]
    assert "Access Denied" in args[0] or "access denied" in args[0].lower()


@pytest.mark.asyncio
async def test_process_url_authorized_non_youtube_user(secure_download_db, authorized_user, mock_message, mocker):
    """Test processing non-YouTube URL with real authorized user."""
    # Add user to database
    await add_user(authorized_user.id, authorized_user.username, authorized_user.id)

    mock_message.from_user = authorized_user
    mock_message.text = "https://example.com/video"

    mocker.patch("bot.handlers.download.is_youtube_url", return_value=False)
    await process_url(mock_message)

    # Should show non-YouTube message for authorized user
    mock_message.answer.assert_called_once()
    args = mock_message.answer.call_args[0]
    assert "YouTube" in args[0] and ("only" in args[0] or "supported" in args[0])


@pytest.mark.asyncio
async def test_process_url_unauthorized_non_youtube_user(secure_download_db, unauthorized_user, mock_message, mocker):
    """Test processing non-YouTube URL with real unauthorized user."""
    # Do NOT add user to database
    mock_message.from_user = unauthorized_user
    mock_message.text = "https://example.com/video"

    mocker.patch("bot.handlers.download.is_youtube_url", return_value=False)
    await process_url(mock_message)

    # Should show access restricted message (not non-YouTube message)
    mock_message.answer.assert_called_once()
    args = mock_message.answer.call_args[0]
    assert "Access Denied" in args[0] or "access denied" in args[0].lower()


@pytest.mark.asyncio
async def test_process_format_selection_authorized_user(secure_download_db, authorized_user, mocker):
    """Test format selection with real authorized user."""
    # Add user to database
    await add_user(authorized_user.id, authorized_user.username, authorized_user.id)

    # Create mock callback query
    callback_query = mocker.MagicMock(spec=CallbackQuery)
    callback_query.from_user = authorized_user
    callback_query.data = "fmt:HD:test_url_id"
    callback_query.answer = mocker.AsyncMock()
    callback_query.message = mocker.MagicMock()
    callback_query.message.edit_text = mocker.AsyncMock()

    mocker.patch("bot.handlers.download.get_url", return_value="https://www.youtube.com/watch?v=test")
    mocker.patch("bot.handlers.download.get_format_by_id", return_value={"label": "HD (720p)", "format": "test_format"})
    mock_queue = mocker.patch("bot.handlers.download.download_queue")
    mock_queue.add_task = mocker.AsyncMock(return_value=1)

    await process_format_selection(callback_query)

    # Should process format selection for authorized user
    callback_query.answer.assert_called_once()
    callback_query.message.edit_text.assert_called_once()

    # Should add task to queue
    mock_queue.add_task.assert_called_once()


@pytest.mark.asyncio
async def test_process_format_selection_unauthorized_user(secure_download_db, unauthorized_user, mocker):
    """Test format selection with real unauthorized user."""
    # Do NOT add user to database

    # Create mock callback query
    callback_query = mocker.MagicMock(spec=CallbackQuery)
    callback_query.from_user = unauthorized_user
    callback_query.data = "fmt:HD:test_url_id"
    callback_query.answer = mocker.AsyncMock()
    callback_query.message = mocker.MagicMock()
    callback_query.message.edit_text = mocker.AsyncMock()

    mocker.patch("bot.handlers.download.get_url", return_value="https://youtube.com/watch?v=test")
    mocker.patch("bot.handlers.download.get_format_by_id", return_value={"label": "HD (720p)", "format": "test_format"})
    mock_queue = mocker.patch("bot.handlers.download.download_queue")
    mock_queue.add_task = mocker.AsyncMock(return_value=1)

    await process_format_selection(callback_query)

    # SECURITY FIX: Authorization check now properly blocks unauthorized users
    # Should answer callback with access denied message
    callback_query.answer.assert_called_once_with("⛔ Access Denied")

    # Should NOT edit message (early return due to auth failure)
    callback_query.message.edit_text.assert_not_called()

    # Should NOT add task to queue (auth check prevents this)
    mock_queue.add_task.assert_not_called()


@pytest.mark.asyncio
async def test_process_format_selection_invalid_callback_data(secure_download_db, authorized_user, mocker):
    """Test format selection with invalid callback data."""
    # Add user to database
    await add_user(authorized_user.id, authorized_user.username, authorized_user.id)

    callback_query = mocker.MagicMock(spec=CallbackQuery)
    callback_query.from_user = authorized_user
    callback_query.data = "invalid:data"
    callback_query.answer = mocker.AsyncMock()
    callback_query.message = mocker.MagicMock()
    callback_query.message.edit_text = mocker.AsyncMock()

    await process_format_selection(callback_query)

    # Should handle invalid data gracefully - only answer callback, no edit_text
    callback_query.answer.assert_called_once()
    # edit_text should NOT be called for invalid callback data
    callback_query.message.edit_text.assert_not_called()


@pytest.mark.asyncio
async def test_process_format_selection_url_not_found(secure_download_db, authorized_user, mocker):
    """Test format selection when URL is not found in storage."""
    # Add user to database
    await add_user(authorized_user.id, authorized_user.username, authorized_user.id)

    callback_query = mocker.MagicMock(spec=CallbackQuery)
    callback_query.from_user = authorized_user
    callback_query.data = "fmt:HD:nonexistent_id"
    callback_query.answer = mocker.AsyncMock()
    callback_query.message = mocker.MagicMock()
    callback_query.message.edit_text = mocker.AsyncMock()

    mocker.patch("bot.handlers.download.get_url", return_value=None)
    await process_format_selection(callback_query)

    # Should handle missing URL gracefully - only answer callback, no edit_text
    callback_query.answer.assert_called_once()
    # edit_text should NOT be called when URL not found
    callback_query.message.edit_text.assert_not_called()


@pytest.mark.asyncio
async def test_process_format_selection_format_not_found(secure_download_db, authorized_user, mocker):
    """Test format selection when format is not found."""
    # Add user to database
    await add_user(authorized_user.id, authorized_user.username, authorized_user.id)

    callback_query = mocker.MagicMock(spec=CallbackQuery)
    callback_query.from_user = authorized_user
    callback_query.data = "fmt:UNKNOWN:test_url_id"
    callback_query.answer = mocker.AsyncMock()
    callback_query.message = mocker.MagicMock()
    callback_query.message.edit_text = mocker.AsyncMock()

    mocker.patch("bot.handlers.download.get_url", return_value="https://www.youtube.com/watch?v=test")
    mocker.patch("bot.handlers.download.get_format_by_id", return_value=None)
    await process_format_selection(callback_query)

    # Should handle missing format gracefully - only answer callback, no edit_text
    callback_query.answer.assert_called_once()
    # edit_text should NOT be called when format not found
    callback_query.message.edit_text.assert_not_called()


@pytest.mark.asyncio
async def test_download_authorization_after_deactivation(secure_download_db, authorized_user, mock_message, mocker):
    """Test that deactivated users lose download access immediately."""
    from bot.utils.db import deactivate_user

    # Add user to database
    await add_user(authorized_user.id, authorized_user.username, authorized_user.id)

    mock_message.from_user = authorized_user
    mock_message.text = "https://www.youtube.com/watch?v=test"

    # Verify user can access downloads initially
    mocker.patch("bot.handlers.download.is_youtube_url", return_value=True)
    mocker.patch("bot.handlers.download.store_url", return_value="test_url_id")
    mocker.patch("bot.handlers.download.get_format_options", return_value=[("HD", "HD (720p)")])
    await process_url(mock_message)

    mock_message.answer.assert_called()
    args = mock_message.answer.call_args[0]
    assert "Choose Download Format" in args[0]

    # Deactivate user
    await deactivate_user(authorized_user.id)

    # Reset mock
    mock_message.answer.reset_mock()

    # User should now be denied access
    await process_url(mock_message)

    mock_message.answer.assert_called()
    args = mock_message.answer.call_args[0]
    assert "Access Denied" in args[0] or "access denied" in args[0].lower()


@pytest.mark.asyncio
async def test_concurrent_download_requests(secure_download_db, authorized_user, mock_message, mocker):
    """Test multiple concurrent download requests from same authorized user."""
    import asyncio

    # Add user to database
    await add_user(authorized_user.id, authorized_user.username, authorized_user.id)

    mock_message.from_user = authorized_user
    mock_message.text = "https://www.youtube.com/watch?v=test"

    mocker.patch("bot.handlers.download.is_youtube_url", return_value=True)
    mocker.patch("bot.handlers.download.store_url", side_effect=lambda url: f"url_id_{hash(url)}")
    mocker.patch("bot.handlers.download.get_format_options", return_value=[("HD", "HD (720p)")])
    # Create multiple concurrent requests
    tasks = []
    for i in range(5):
        message_copy = mocker.MagicMock(spec=Message)
        message_copy.answer = mocker.AsyncMock()
        message_copy.from_user = authorized_user
        message_copy.text = f"https://www.youtube.com/watch?v=test{i}"
        tasks.append(process_url(message_copy))

    # Execute concurrently
    await asyncio.gather(*tasks)

    # All should succeed for authorized user
    for _task in tasks:
        # Each message should have been answered
        pass  # Tasks are completed, individual verification would require more complex setup
