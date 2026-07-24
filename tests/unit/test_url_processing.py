"""Tests for URL processing in download handlers."""

import pytest
from aiogram.types import InlineKeyboardMarkup, Message, User

from bot.handlers.download import process_format_selection, process_url
from bot.services.storage import get_url


class TestProcessUrlHandler:
    """Tests for the process_url handler function."""

    @pytest.mark.asyncio
    async def test_unauthorized_user(self, mocker):
        """Test response when an unauthorized user sends a URL."""
        # Setup
        mock_user = mocker.MagicMock(spec=User)
        mock_user.id = 999999
        mock_message = mocker.MagicMock(spec=Message)
        mock_message.answer = mocker.AsyncMock()
        mock_message.from_user = mock_user
        mock_message.text = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"

        # Execute with unauthorized user
        mocker.patch(
            "bot.handlers.download.is_user_authorized",
            mocker.AsyncMock(return_value=False),
        )
        await process_url(mock_message)

        # Verify
        mock_message.answer.assert_called_once()
        args = mock_message.answer.call_args[0][0]
        assert "Access Denied" in args
        assert "don't have permission" in args

    @pytest.mark.asyncio
    async def test_non_youtube_url(self, mocker):
        """Test response when a user sends a non-YouTube URL."""
        # Setup
        mock_user = mocker.MagicMock(spec=User)
        mock_user.id = 123456
        mock_message = mocker.MagicMock(spec=Message)
        mock_message.answer = mocker.AsyncMock()
        mock_message.from_user = mock_user
        mock_message.text = "https://example.com/some/video"

        # Execute with non-YouTube URL
        mocker.patch(
            "bot.handlers.download.is_user_authorized",
            mocker.AsyncMock(return_value=True),
        )
        mocker.patch("bot.handlers.download.is_youtube_url", return_value=False)
        await process_url(mock_message)

        # Verify
        mock_message.answer.assert_called_once()
        args = mock_message.answer.call_args[0][0]
        assert "Unsupported URL" in args
        assert "valid YouTube link" in args

    @pytest.mark.asyncio
    async def test_valid_youtube_url_format_selection(self, mocker):
        """Test format selection for a valid YouTube URL."""
        # Setup
        mock_user = mocker.MagicMock(spec=User)
        mock_user.id = 123456
        mock_message = mocker.MagicMock(spec=Message)
        mock_message.answer = mocker.AsyncMock()
        mock_message.from_user = mock_user
        mock_message.text = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"

        test_formats = [
            ("video:HD", "HD Video (720p)"),
            ("video:FHD", "Full HD Video (1080p)"),
            ("audio:mp3", "MP3 Audio (320kbps)"),
        ]

        # Execute with valid YouTube URL
        mocker.patch(
            "bot.handlers.download.is_user_authorized",
            mocker.AsyncMock(return_value=True),
        )
        mocker.patch("bot.handlers.download.is_youtube_url", return_value=True)
        mocker.patch("bot.handlers.download.store_url", return_value="test_url_id")
        mocker.patch(
            "bot.handlers.download.get_format_options",
            return_value=test_formats,
        )
        await process_url(mock_message)

        # Verify answer was called with format selection
        mock_message.answer.assert_called_once()
        args, kwargs = mock_message.answer.call_args

        # Check message content
        assert "Choose Download Format" in args[0]

        # Check keyboard markup
        assert "reply_markup" in kwargs
        markup = kwargs["reply_markup"]
        assert isinstance(markup, InlineKeyboardMarkup)

        # Check buttons
        keyboard = markup.inline_keyboard
        assert len(keyboard) > 0  # At least one row

        # Verify all formats are included in the keyboard
        all_buttons = []
        for row in keyboard:
            all_buttons.extend(row)

        # Check number of buttons matches number of formats
        assert len(all_buttons) == len(test_formats)

        # Check callback data format for all buttons
        for i, button in enumerate(all_buttons):
            assert button.callback_data.startswith("fmt:")
            assert "test_url_id" in button.callback_data
            format_id, label = test_formats[i]
            assert format_id in button.callback_data
            assert button.text == label


class TestFormatSelectionHandler:
    """Tests for the process_format_selection handler function."""

    @pytest.fixture
    def mock_callback_query(self, mocker):
        """Create a mock callback query."""
        mock = mocker.MagicMock()
        mock.from_user = mocker.MagicMock()
        mock.from_user.id = 123456
        mock.message = mocker.MagicMock()
        mock.message.chat.id = 123456
        mock.answer = mocker.AsyncMock()
        mock.message.edit_text = mocker.AsyncMock()
        return mock

    @pytest.mark.asyncio
    async def test_invalid_format_not_enough_parts(self, mock_callback_query, mocker):
        """Test handling of invalid callback data with too few parts."""
        # Setup invalid callback data (missing parts)
        mock_callback_query.data = "fmt:missing_parts"  # Only 2 parts, needs at least 3

        # Execute
        mocker.patch("bot.handlers.download.is_user_authorized", return_value=True)
        mock_logger = mocker.patch("bot.handlers.download.logger.error")
        await process_format_selection(mock_callback_query)

        # Verify that the error was logged
        mock_logger.assert_called()
        assert "Invalid format selection" in mock_logger.call_args[0][0]

        # Verify error message to user
        mock_callback_query.answer.assert_called_once_with("Invalid format selection")

    @pytest.mark.asyncio
    async def test_invalid_callback_data_wrong_prefix(self, mock_callback_query, mocker):
        """Test handling of invalid callback data with wrong prefix."""
        # Setup invalid callback data (wrong prefix)
        mock_callback_query.data = "wrong:video:HD:12345"  # Starts with 'wrong' not 'fmt'

        # Execute
        # This would be filtered by the router before reaching our handler
        # For test, we just verify it doesn't throw errors
        mocker.patch("bot.handlers.download.is_user_authorized", return_value=True)
        await process_format_selection(mock_callback_query)

    @pytest.mark.asyncio
    async def test_url_not_found(self, mock_callback_query, mocker):
        """Test handling of URL not found in storage."""
        # Setup
        mock_callback_query.data = "fmt:video:HD:nonexistent_id"

        # Execute with URL not found
        mocker.patch("bot.handlers.download.is_user_authorized", return_value=True)
        mocker.patch("bot.handlers.download.get_url", return_value=None)
        await process_format_selection(mock_callback_query)

        # Verify error message
        mock_callback_query.answer.assert_called_once_with("URL not found or expired")

    @pytest.mark.asyncio
    async def test_format_not_found(self, mock_callback_query, mocker):
        """Test handling of format not found."""
        # Setup
        mock_callback_query.data = "fmt:invalid:format:test_id"

        # Execute with format not found
        mocker.patch("bot.handlers.download.is_user_authorized", return_value=True)
        mocker.patch(
            "bot.handlers.download.get_url",
            return_value="https://example.com",
        )
        mocker.patch("bot.handlers.download.get_format_by_id", return_value=None)
        await process_format_selection(mock_callback_query)

        # Verify error message
        mock_callback_query.answer.assert_called_once_with("Selected format not found")

    @pytest.mark.asyncio
    async def test_successful_format_selection_no_queue(self, mock_callback_query, mocker):
        """Test successful format selection with no queue."""
        # Setup
        mock_callback_query.data = "fmt:video:HD:test_id"
        test_url = "https://www.youtube.com/watch?v=test123"
        format_data = {
            "label": "HD Video (720p)",
            "format": "bestvideo[height<=720]+bestaudio/best[height<=720]",
            "type": "video",
        }

        status_message = mocker.MagicMock()
        mock_callback_query.message.edit_text.return_value = status_message

        mocker.patch("bot.handlers.download.is_user_authorized", return_value=True)
        mocker.patch("bot.handlers.download.get_url", return_value=test_url)
        mocker.patch(
            "bot.handlers.download.get_format_by_id",
            return_value=format_data,
        )
        mocker.patch("bot.handlers.download.store_format")
        mocker.patch("bot.handlers.download.get_bot")
        mocker.patch("bot.handlers.download.download_queue.is_processing", False)
        mocker.patch(
            "bot.handlers.download.download_queue.is_user_in_queue",
            return_value=False,
        )
        mocker.patch(
            "bot.handlers.download.download_queue.add_task",
            mocker.AsyncMock(return_value=1),
        )
        await process_format_selection(mock_callback_query)

        # Verify callback was acknowledged
        mock_callback_query.answer.assert_called_once()
        assert "Processing your request" in mock_callback_query.answer.call_args[0][0]

        # Verify message was edited
        mock_callback_query.message.edit_text.assert_called_once()
        edit_call_args = mock_callback_query.message.edit_text.call_args
        edited_text = edit_call_args[0][0]
        assert "Download" in edited_text
        assert format_data["label"] in edited_text
        assert test_url in edited_text
        assert "Starting download now" in edited_text

    @pytest.mark.asyncio
    async def test_format_selection_with_queue(self, mock_callback_query, mocker):
        """Test format selection when already in queue."""
        # Setup
        mock_callback_query.data = "fmt:video:HD:test_id"
        test_url = "https://www.youtube.com/watch?v=test123"
        format_data = {
            "label": "HD Video (720p)",
            "format": "bestvideo[height<=720]+bestaudio/best[height<=720]",
            "type": "video",
        }

        status_message = mocker.MagicMock()
        mock_callback_query.message.edit_text.return_value = status_message

        mock_bot = mocker.MagicMock()
        mock_bot.edit_message_text = mocker.AsyncMock()

        mocker.patch("bot.handlers.download.is_user_authorized", return_value=True)
        mocker.patch("bot.handlers.download.get_url", return_value=test_url)
        mocker.patch(
            "bot.handlers.download.get_format_by_id",
            return_value=format_data,
        )
        mocker.patch("bot.handlers.download.store_format")
        mocker.patch("bot.handlers.download.get_bot", return_value=mock_bot)
        mocker.patch("bot.handlers.download.download_queue.is_processing", True)
        mocker.patch(
            "bot.handlers.download.download_queue.is_user_in_queue",
            return_value=True,
        )
        mocker.patch(
            "bot.handlers.download.download_queue.add_task",
            mocker.AsyncMock(return_value=3),
        )
        await process_format_selection(mock_callback_query)

        # Verify callback was acknowledged
        mock_callback_query.answer.assert_called_once()

        # Verify message was edited
        mock_callback_query.message.edit_text.assert_called_once()
        edit_call_args = mock_callback_query.message.edit_text.call_args
        edited_text = edit_call_args[0][0]
        assert "Download queued" in edited_text
        assert "You already have downloads in the queue" in edited_text

        # Verify queue position update
        mock_bot.edit_message_text.assert_called_once()
        bot_call_args = mock_bot.edit_message_text.call_args
        queue_text = bot_call_args[0][0]
        assert "Queue position: 3" in queue_text


class TestStorageIntegration:
    """Tests for integration with storage module."""

    def test_url_storage_lifecycle(self, mocker):
        """Test the URL lifecycle in storage during processing."""
        test_url = "https://example.com/test"
        test_id = "test123"

        # Test with patched storage
        mocker.patch("bot.services.storage.URL_STORAGE", {})
        # Manually import to get the patched version
        # Store a URL manually (format: url, format_id, timestamp)
        import time

        from bot.services.storage import (
            URL_STORAGE,
            clear_url,
            get_format,
            store_format,
        )

        URL_STORAGE[test_id] = (test_url, None, time.time())

        # Verify URL can be retrieved
        assert get_url(test_id) == test_url
        assert get_format(test_id) is None

        # Store format
        store_format(test_id, "video:HD")
        assert get_format(test_id) == "video:HD"

        # Clear URL
        clear_url(test_id)
        assert get_url(test_id) is None
        assert test_id not in URL_STORAGE
