"""Tests for command handlers."""

import pytest
from aiogram import Bot

from bot.handlers.commands import (
    command_adduser,
    command_cancel,
    command_help,
    command_invite,
    command_start,
)


@pytest.mark.asyncio
@pytest.mark.parametrize("user_id,is_auth,expected_text", [
    (123456, True, "VideoGrabberBot Help"),
    (999999, False, "Access Restricted"),
])
async def test_help_command(mocker, make_message_mock, user_id, is_auth, expected_text):
    """Test /help command for authorized and unauthorized users."""
    mock_message = make_message_mock(user_id)
    mocker.patch("bot.handlers.commands.is_user_authorized", mocker.AsyncMock(return_value=is_auth))

    await command_help(mock_message)

    mock_message.answer.assert_called_once()
    assert expected_text in mock_message.answer.call_args[0][0]


@pytest.mark.asyncio
@pytest.mark.parametrize("user_id,is_auth,expected_text", [
    (123456, True, "Welcome to VideoGrabberBot"),
    (999999, False, "Access Restricted"),
])
async def test_start_command_auth(mocker, make_message_mock, user_id, is_auth, expected_text):
    """Test /start command for authorized and unauthorized users (no invite)."""
    mock_message = make_message_mock(user_id, text="/start")
    mock_message.from_user.username = f"user_{user_id}"
    mocker.patch("bot.handlers.commands.is_user_authorized", mocker.AsyncMock(return_value=is_auth))
    mocker.patch("bot.handlers.commands.logger.info", mocker.MagicMock())

    await command_start(mock_message)

    mock_message.answer.assert_called_once()
    assert expected_text in mock_message.answer.call_args[0][0]


@pytest.mark.asyncio
@pytest.mark.parametrize("invite_valid,expected_fragment", [
    (True, "Welcome"),
    (False, "Invalid Invite"),
])
async def test_start_command_with_invite_code(mocker, make_message_mock, invite_valid, expected_fragment):
    """Test /start command with invite code — valid and invalid cases."""
    mock_message = make_message_mock(999999, text="/start INVITE123")
    mock_message.from_user.username = "new_user"
    mocker.patch("bot.handlers.commands.use_invite", mocker.AsyncMock(return_value=invite_valid))
    mocker.patch("bot.handlers.commands.logger.info", mocker.MagicMock())
    mocker.patch("bot.handlers.commands.logger.warning", mocker.MagicMock())

    await command_start(mock_message)

    mock_message.answer.assert_called_once()
    assert expected_fragment in mock_message.answer.call_args[0][0]


@pytest.mark.asyncio
@pytest.mark.parametrize("user_id,is_auth,in_queue,removed,expected_text", [
    (999999, False, False, 0, "Access Restricted"),
    (123456, True, False, 0, "No Active Downloads"),
    (123456, True, True, 2, "Downloads Cancelled"),
])
async def test_cancel_command(mocker, make_message_mock, user_id, is_auth, in_queue, removed, expected_text):
    """Test /cancel command: unauthorized, no downloads, and with active downloads."""
    mock_message = make_message_mock(user_id)
    mocker.patch("bot.handlers.commands.is_user_authorized", mocker.AsyncMock(return_value=is_auth))

    if is_auth:
        mock_queue = mocker.MagicMock()
        mock_queue.is_user_in_queue.return_value = in_queue
        mock_queue.clear_user_tasks = mocker.AsyncMock(return_value=removed)
        mocker.patch("bot.services.queue.download_queue", mock_queue)

    await command_cancel(mock_message)

    mock_message.answer.assert_called_once()
    args = mock_message.answer.call_args[0][0]
    assert expected_text in args

    if is_auth:
        mock_queue.is_user_in_queue.assert_called_once_with(user_id)
        if in_queue:
            assert f"{removed} downloads" in args
            mock_queue.clear_user_tasks.assert_called_once_with(user_id)
        else:
            mock_queue.clear_user_tasks.assert_not_called()


@pytest.mark.asyncio
async def test_invite_command_success(mocker, make_message_mock):
    """Test /invite command with successful invite creation."""
    mock_message = make_message_mock(123456)

    mock_bot_info = mocker.MagicMock()
    mock_bot_info.username = "test_bot"
    mock_bot = mocker.MagicMock(spec=Bot)
    mock_bot.get_me = mocker.AsyncMock(return_value=mock_bot_info)
    mock_message.bot = mock_bot

    mocker.patch("bot.handlers.commands.is_user_authorized", mocker.AsyncMock(return_value=True))
    mocker.patch("bot.handlers.commands.create_invite", mocker.AsyncMock(return_value="test_invite_code"))
    mocker.patch("bot.handlers.commands.logger.info", mocker.MagicMock())

    await command_invite(mock_message)

    mock_message.answer.assert_called_once()
    args = mock_message.answer.call_args[0][0]
    assert "Invite Link Generated" in args
    assert "https://t.me/test_bot?start=test_invite_code" in args


@pytest.mark.asyncio
async def test_invite_command_failure(mocker, make_message_mock):
    """Test /invite command with failed invite creation."""
    mock_message = make_message_mock(123456)

    mocker.patch("bot.handlers.commands.is_user_authorized", mocker.AsyncMock(return_value=True))
    mocker.patch("bot.handlers.commands.create_invite", mocker.AsyncMock(return_value=None))
    mocker.patch("bot.handlers.commands.logger.error", mocker.MagicMock())

    await command_invite(mock_message)

    mock_message.answer.assert_called_once()
    args = mock_message.answer.call_args[0][0]
    assert "Error" in args
    assert "Could not generate invite link" in args


@pytest.mark.asyncio
async def test_invite_command_unauthorized(mocker, make_message_mock):
    """Test /invite command with unauthorized user."""
    mock_message = make_message_mock(999999)

    mocker.patch("bot.handlers.commands.is_user_authorized", mocker.AsyncMock(return_value=False))

    await command_invite(mock_message)

    mock_message.answer.assert_called_once()
    assert "Access Restricted" in mock_message.answer.call_args[0][0]


@pytest.mark.asyncio
async def test_adduser_command_non_admin(mocker, make_message_mock):
    """Test /adduser command with non-admin user."""
    mock_message = make_message_mock(999999)

    mocker.patch("bot.handlers.commands.ADMIN_USER_ID", 123456)
    mocker.patch("bot.handlers.commands.logger.warning", mocker.MagicMock())

    await command_adduser(mock_message)

    mock_message.answer.assert_called_once()
    assert "Admin Only" in mock_message.answer.call_args[0][0]


@pytest.mark.asyncio
async def test_adduser_command_missing_args(mocker, make_message_mock):
    """Test /adduser command without arguments."""
    mock_message = make_message_mock(123456, text="/adduser")

    mocker.patch("bot.handlers.commands.ADMIN_USER_ID", 123456)

    await command_adduser(mock_message)

    mock_message.answer.assert_called_once()
    args = mock_message.answer.call_args[0][0]
    assert "Usage Error" in args
    assert "Please provide a username or user ID" in args


@pytest.mark.asyncio
async def test_adduser_command_with_userid_success(mocker, make_message_mock):
    """Test /adduser command with user ID (success case)."""
    mock_message = make_message_mock(123456, text="/adduser 789012")

    mocker.patch("bot.handlers.commands.ADMIN_USER_ID", 123456)
    mocker.patch("bot.handlers.commands.add_user", mocker.AsyncMock(return_value=True))
    mocker.patch("bot.handlers.commands.logger.info", mocker.MagicMock())

    await command_adduser(mock_message)

    mock_message.answer.assert_called_once()
    args = mock_message.answer.call_args[0][0]
    assert "User Added" in args
    assert "789012" in args


@pytest.mark.asyncio
async def test_adduser_command_with_userid_already_exists(mocker, make_message_mock):
    """Test /adduser command with user ID that already exists."""
    mock_message = make_message_mock(123456, text="/adduser 789012")

    mocker.patch("bot.handlers.commands.ADMIN_USER_ID", 123456)
    mocker.patch("bot.handlers.commands.add_user", mocker.AsyncMock(return_value=False))

    await command_adduser(mock_message)

    mock_message.answer.assert_called_once()
    args = mock_message.answer.call_args[0][0]
    assert "User Already Exists" in args
    assert "789012" in args


@pytest.mark.asyncio
async def test_adduser_command_with_username(mocker, make_message_mock):
    """Test /adduser command with username instead of user ID."""
    mock_message = make_message_mock(123456, text="/adduser @test_user")

    mocker.patch("bot.handlers.commands.ADMIN_USER_ID", 123456)
    mocker.patch("bot.handlers.commands.logger.info", mocker.MagicMock())

    await command_adduser(mock_message)

    mock_message.answer.assert_called_once()
    args = mock_message.answer.call_args[0][0]
    assert "User Cannot Be Added Directly by Username" in args
    assert "@test_user" in args
