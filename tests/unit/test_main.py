"""Tests for main module initialization and startup."""

import pytest
from aiogram import Dispatcher

from bot.main import startup


@pytest.mark.asyncio
async def test_startup(mocker):
    """Test startup function initializes required components."""
    # Mock the dependencies
    mock_init_db = mocker.patch("bot.main.init_db", mocker.AsyncMock())
    mock_bot = mocker.patch("bot.main.bot", mocker.MagicMock())

    # Configure bot.set_my_commands mock
    mock_bot.set_my_commands = mocker.AsyncMock()

    # Call the startup function
    await startup()

    # Verify database initialization (called once after code deduplication)
    assert mock_init_db.call_count == 1, "Database should be initialized once"

    # Verify bot commands setup (called once after code deduplication)
    assert mock_bot.set_my_commands.call_count == 1

    # Verify the correct commands were registered
    commands_arg = mock_bot.set_my_commands.call_args[0][0]
    assert isinstance(commands_arg, list)
    assert len(commands_arg) >= 1

    # Check command structure
    command_names = [cmd.command for cmd in commands_arg]
    assert "start" in command_names
    assert "help" in command_names


@pytest.mark.asyncio
async def test_main_routers(mocker):
    """Test main function registers routers correctly."""
    # Mock the dispatcher and dependencies
    mock_dp = mocker.MagicMock(spec=Dispatcher)
    mock_dp.include_router = mocker.MagicMock()
    mock_dp.start_polling = mocker.AsyncMock()

    # Mock other dependencies
    mocker.patch("bot.main.dp", mock_dp)
    mocker.patch("bot.main.commands_router", "commands_router_mock")
    mocker.patch("bot.main.download_router", "download_router_mock")
    mock_startup = mocker.patch("bot.main.startup", mocker.AsyncMock())
    mocker.patch("bot.main.bot", "bot_mock")

    # Import and call the main function
    from bot.main import main

    await main()

    # Verify routers were registered
    assert mock_dp.include_router.call_count == 2, "Should register 2 routers"

    # Check router registration order
    mock_dp.include_router.assert_any_call("commands_router_mock")
    mock_dp.include_router.assert_any_call("download_router_mock")

    # Verify startup was called
    assert mock_startup.call_count == 1, "Startup should be called once"

    # Verify polling was started
    mock_dp.start_polling.assert_called_once_with("bot_mock")
