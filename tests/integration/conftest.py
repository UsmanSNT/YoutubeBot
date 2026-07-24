"""Configuration and fixtures for integration tests."""

import asyncio
import tempfile
from pathlib import Path

import pytest
import pytest_asyncio
from aiogram import Bot, Dispatcher
from aiogram.types import CallbackQuery, Chat, Message, User

from bot import config
from bot.handlers.commands import router as commands_router
from bot.handlers.download import download_router
from bot.services.queue import download_queue


@pytest_asyncio.fixture
async def temp_db(monkeypatch):
    """Create a temporary database for testing."""
    # Create temp directory and file
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_db_path = Path(temp_dir) / "test_bot.db"
        temp_dir_path = Path(temp_dir)

        # Patch DB_PATH and TEMP_DIR in the config module
        from bot.utils import db as db_module

        monkeypatch.setattr(db_module, "DB_PATH", temp_db_path)
        monkeypatch.setattr(config, "DB_PATH", temp_db_path)
        monkeypatch.setattr(config, "TEMP_DIR", temp_dir_path)
        monkeypatch.setattr(config, "DATA_DIR", temp_dir_path)

        # Initialize database
        from bot.utils.db import init_db

        await init_db()

        yield temp_db_path


@pytest_asyncio.fixture
async def mock_bot(mocker):
    """Create a mocked bot instance."""
    # Create a properly mocked bot instance
    bot = mocker.MagicMock(spec=Bot)
    bot.send_message = mocker.AsyncMock(return_value=mocker.MagicMock(message_id=100))
    bot.edit_message_text = mocker.AsyncMock()
    bot.send_document = mocker.AsyncMock()

    # Make get_me return a proper object with username
    bot_info = mocker.MagicMock()
    bot_info.username = "test_bot"
    bot.get_me = mocker.AsyncMock(return_value=bot_info)

    # Patch the get_bot function to return our mock
    mocker.patch("bot.telegram_api.client.get_bot", return_value=bot)
    yield bot


@pytest_asyncio.fixture
async def mock_dispatcher(mocker):
    """Create a mocked dispatcher instance."""
    dp = mocker.MagicMock(spec=Dispatcher)
    dp.include_router = mocker.MagicMock()
    dp.start_polling = mocker.AsyncMock()

    # Add our routers
    dp.include_router(commands_router)
    dp.include_router(download_router)

    return dp


@pytest_asyncio.fixture
async def authorized_user(mocker):
    """Create an authorized user for testing."""
    from bot.utils.db import add_user

    user_id = 123456789
    username = "test_user"

    await add_user(user_id, username, config.ADMIN_USER_ID)

    # Create a mock user object
    user = mocker.MagicMock(spec=User)
    user.id = user_id
    user.username = username

    return user


@pytest_asyncio.fixture
async def unauthorized_user(mocker):
    """Create an unauthorized user for testing."""
    user = mocker.MagicMock(spec=User)
    user.id = 999999999
    user.username = "unauthorized_user"

    return user


@pytest_asyncio.fixture
async def mock_message(mocker, authorized_user, mock_bot):
    """Create a mock message for testing."""
    message = mocker.MagicMock(spec=Message)
    message.from_user = authorized_user
    message.chat = mocker.MagicMock(spec=Chat, id=authorized_user.id)
    message.answer = mocker.AsyncMock(return_value=mocker.MagicMock(message_id=101))
    message.message_id = 101
    message.bot = mock_bot

    return message


@pytest_asyncio.fixture
async def mock_callback_query(mocker, authorized_user, mock_message):
    """Create a mock callback query for testing."""
    callback = mocker.MagicMock(spec=CallbackQuery)
    callback.from_user = authorized_user

    # Reuse mock_message to keep state consistent
    mock_message.edit_text = mocker.AsyncMock(return_value=mocker.MagicMock(message_id=102))
    callback.message = mock_message
    callback.answer = mocker.AsyncMock()

    return callback


@pytest_asyncio.fixture
async def reset_queue():
    """Reset the download queue between tests."""
    # Clear the queue before test
    download_queue.queue = asyncio.Queue()
    download_queue.is_processing = False
    download_queue.current_task = None

    yield

    # Clear the queue after test
    download_queue.queue = asyncio.Queue()
    download_queue.is_processing = False
    download_queue.current_task = None


@pytest_asyncio.fixture
async def mock_download_system(mocker):
    """Mock the entire download system with common patterns."""
    return {
        "download_video": mocker.patch("bot.services.downloader.download_youtube_video", mocker.AsyncMock()),
        "store_url": mocker.patch("bot.handlers.download.store_url", return_value="test_url_id"),
        "get_url": mocker.patch(
            "bot.handlers.download.get_url", return_value="https://www.youtube.com/watch?v=test_video"
        ),
        "is_youtube_url": mocker.patch("bot.handlers.download.is_youtube_url", return_value=True),
    }


@pytest_asyncio.fixture
async def mock_format_system(mocker):
    """Mock the format system with standard format configurations."""
    standard_format = {
        "label": "HD (720p)",
        "format": "best[height<=720]",
        "type": "video",
    }

    available_formats = {
        "video:SD": {
            "label": "SD (480p)",
            "format": "best[height<=480]",
            "type": "video",
        },
        "video:HD": {
            "label": "HD (720p)",
            "format": "best[height<=720]",
            "type": "video",
        },
    }

    return {
        "get_format_by_id": mocker.patch("bot.services.formats.get_format_by_id", return_value=standard_format),
        "get_available_formats": mocker.patch(
            "bot.services.formats.get_available_formats", return_value=available_formats
        ),
    }


@pytest_asyncio.fixture
async def mock_telegram_system(mocker, mock_bot):
    """Mock the Telegram API system."""
    return {
        "get_bot": mocker.patch("bot.telegram_api.client.get_bot", return_value=mock_bot),
    }


@pytest_asyncio.fixture
async def mock_command_system(mocker):
    """Mock the command system with common patterns."""
    return {
        "create_invite": mocker.patch(
            "bot.handlers.commands.create_invite", mocker.AsyncMock(return_value="test_invite")
        ),
        "add_user_success": mocker.patch("bot.handlers.commands.add_user", mocker.AsyncMock(return_value=True)),
    }


@pytest_asyncio.fixture
async def mock_error_system(mocker):
    """Mock the error handling system."""
    return {
        "notify_admin": mocker.patch("bot.utils.logging.notify_admin", mocker.AsyncMock()),
    }


@pytest_asyncio.fixture
async def mock_complete_system(mock_download_system, mock_format_system, mock_telegram_system):
    """Composite fixture combining the most commonly used mocks."""
    return {
        "download": mock_download_system,
        "format": mock_format_system,
        "telegram": mock_telegram_system,
    }


@pytest_asyncio.fixture
async def integration_setup(mocker, temp_db, mock_bot, authorized_user, reset_queue, mock_complete_system):
    """Setup for integration tests with all components initialized."""
    # The mocking is now handled by mock_complete_system fixture
    yield {"bot": mock_bot, "user": authorized_user, "db_path": temp_db}


def pytest_configure(config):
    """Configure pytest for integration tests."""
    # Add xdist group markers to integration tests to avoid parallel execution conflicts
    config.addinivalue_line(
        "markers", "integration: mark test as integration test (runs sequentially to avoid race conditions)"
    )


def pytest_collection_modifyitems(config, items):
    """Modify test collection to group integration tests."""
    # Add xdist_group marker to all integration tests to run them in same worker
    for item in items:
        if item.get_closest_marker("integration"):
            # Add the xdist_group marker to run all integration tests in same worker
            item.add_marker(pytest.mark.xdist_group(name="integration"))
