"""Tests for the logging module."""

from pathlib import Path

import pytest
from loguru import logger

from bot.utils.logging import notify_admin, setup_logger


class LoggerMock:
    """Mock class for logger functions."""

    def __init__(self):
        """Initialize mock logger."""
        self.remove_called = False
        self.add_calls = []
        self.info_called = False
        self.log_called = False
        self.error_called = False
        self.error_message = None

    def remove(self):
        """Mock logger remove method."""
        self.remove_called = True

    def add(self, sink, **kwargs):
        """Mock logger add method."""
        self.add_calls.append((sink, kwargs))

    def info_method(self, message):
        """Mock logger info method."""
        self.info_called = True

    def log(self, level, message, **kwargs):
        """Mock logger log method."""
        self.log_called = True

    def error(self, message, **kwargs):
        """Mock logger error method."""
        self.error_called = True
        self.error_message = message


class BotMockSuccess:
    """Mock bot that succeeds in sending messages."""

    def __init__(self):
        """Initialize mock bot."""
        self.send_message_called = False
        self.send_message_args = None

    async def send_message(self, chat_id, text):
        """Mock successful send_message."""
        self.send_message_called = True
        self.send_message_args = (chat_id, text)


class BotMockFailure:
    """Mock bot that fails when sending messages."""

    async def send_message(self, chat_id, text):
        """Mock failing send_message."""
        raise Exception("Test error")


class BotMockWithKwargs:
    """Mock bot for testing kwargs functionality."""

    def __init__(self):
        """Initialize mock bot."""
        self.send_message_text = None

    async def send_message(self, chat_id, text):
        """Mock send_message that captures text."""
        self.send_message_text = text


def test_setup_logger(monkeypatch):
    """Test logger setup."""
    # Create mock logger
    mock_logger = LoggerMock()

    # Apply mocks
    monkeypatch.setattr(logger, "remove", mock_logger.remove)
    monkeypatch.setattr(logger, "add", mock_logger.add)
    monkeypatch.setattr(logger, "info", mock_logger.info_method)

    # Call the setup function
    temp_log_file = Path("test_log.log")
    setup_logger(temp_log_file)

    # Verify that logger was configured correctly
    assert mock_logger.remove_called

    # Check that add was called for both stdout and file
    assert len(mock_logger.add_calls) == 2

    # Check that info was called (initialization message)
    assert mock_logger.info_called


def test_setup_logger_default_path(monkeypatch):
    """Test logger setup with default log path."""
    # Create mock logger
    mock_logger = LoggerMock()

    # Mock Path
    mock_data_dir = Path("/mock/data/dir")

    # Apply mocks
    monkeypatch.setattr(logger, "remove", mock_logger.remove)
    monkeypatch.setattr(logger, "add", mock_logger.add)
    monkeypatch.setattr(logger, "info", mock_logger.info_method)
    monkeypatch.setattr("bot.utils.logging.DATA_DIR", mock_data_dir)

    # Call the setup function with default path
    setup_logger()

    # Verify that logger was configured correctly
    assert mock_logger.remove_called

    # Check that add was called for both stdout and file
    assert len(mock_logger.add_calls) == 2

    # Check that default path was used
    file_sink = mock_logger.add_calls[1][0]
    assert str(mock_data_dir / "bot.log") == str(file_sink)


@pytest.mark.asyncio
async def test_notify_admin_success(monkeypatch):
    """Test that admin notifications are sent successfully."""
    # Create mock bot and logger
    mock_bot = BotMockSuccess()
    mock_logger = LoggerMock()

    monkeypatch.setattr(logger, "log", mock_logger.log)

    # Test message
    test_message = "Test notification"

    # Call the function
    await notify_admin(mock_bot, test_message, level="INFO")

    # Verify that send_message was called
    assert mock_bot.send_message_called
    # Check arguments
    assert "Test notification" in mock_bot.send_message_args[1]
    assert mock_logger.log_called


@pytest.mark.asyncio
async def test_notify_admin_error_level(mocker, monkeypatch):
    """Test that error-level notifications use logger.error."""
    # Create mock bot and logger
    mock_bot = mocker.AsyncMock()
    mock_logger = LoggerMock()

    # Apply mock
    monkeypatch.setattr(logger, "error", mock_logger.error)
    monkeypatch.setattr(logger, "log", mocker.MagicMock())

    # Call the function with ERROR level
    await notify_admin(mock_bot, "Error message", level="ERROR")

    # Verify logger.error was called
    assert mock_logger.error_called
    assert "Error message" in mock_logger.error_message


@pytest.mark.asyncio
async def test_notify_admin_error(monkeypatch):
    """Test handling of errors during admin notification."""
    # Create mock bot that raises an exception
    mock_bot = BotMockFailure()
    mock_logger = LoggerMock()

    monkeypatch.setattr(logger, "error", mock_logger.error)

    # Call the function
    await notify_admin(mock_bot, "Test message")

    # Verify that error was logged
    assert mock_logger.error_message is not None
    assert "Failed to notify admin" in mock_logger.error_message


@pytest.mark.asyncio
async def test_notify_admin_with_kwargs(monkeypatch):
    """Test that additional kwargs are included in the notification."""
    # Create mock bot
    mock_bot = BotMockWithKwargs()

    # Mock logger functions
    monkeypatch.setattr(logger, "log", lambda *args, **kwargs: None)

    # Call with additional data
    await notify_admin(
        mock_bot,
        "Test with data",
        level="WARNING",
        user_id=12345,
        action="test_action",
    )

    # Check message content includes the additional data
    assert "Test with data" in mock_bot.send_message_text
    assert "user_id: 12345" in mock_bot.send_message_text
    assert "action: test_action" in mock_bot.send_message_text


@pytest.mark.asyncio
async def test_notify_admin_log_failure(mocker, monkeypatch):
    """Test that failure in _log_admin_message is handled gracefully."""
    mock_bot = mocker.AsyncMock()

    mocker.patch("bot.utils.logging._log_admin_message", side_effect=Exception("Log failure"))
    mock_error = mocker.MagicMock()
    monkeypatch.setattr(logger, "error", mock_error)

    await notify_admin(mock_bot, "Test message")

    mock_bot.send_message.assert_not_called()
    assert any("Failed to log admin message" in str(call) for call in mock_error.call_args_list)


@pytest.mark.asyncio
async def test_notify_admin_format_failure(mocker, monkeypatch):
    """Test that failure in _format_admin_message is handled gracefully."""
    mock_bot = mocker.AsyncMock()

    monkeypatch.setattr(logger, "log", mocker.MagicMock())
    mocker.patch("bot.utils.logging._format_admin_message", side_effect=Exception("Format failure"))
    mock_error = mocker.MagicMock()
    monkeypatch.setattr(logger, "error", mock_error)

    await notify_admin(mock_bot, "Test message", level="INFO")

    mock_bot.send_message.assert_not_called()
    assert any("Failed to format admin message" in str(call) for call in mock_error.call_args_list)
