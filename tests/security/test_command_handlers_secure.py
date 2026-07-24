"""Secure tests for command handlers using real authorization.

This replaces the dangerous mocking of is_user_authorized with real database testing.
"""

import tempfile
from pathlib import Path

import pytest
import pytest_asyncio
from aiogram.types import Message, User

from bot.handlers.commands import (
    command_adduser,
    command_cancel,
    command_help,
    command_invite,
    command_start,
)
from bot.utils.db import add_user, init_db


@pytest_asyncio.fixture
async def secure_command_db(mocker):
    """Create real database for command testing."""
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_db_path = Path(temp_dir) / "command_test.db"

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
    message.chat = mocker.MagicMock()
    message.chat.id = 123456789
    return message


@pytest.mark.asyncio
async def test_help_command_authorized_user(secure_command_db, authorized_user, mock_message):
    """Test /help command with real authorized user."""
    # Add user to database (real authorization)
    await add_user(authorized_user.id, authorized_user.username, authorized_user.id)

    mock_message.from_user = authorized_user

    # Call help command - uses real is_user_authorized
    await command_help(mock_message)

    # Verify help message was sent
    mock_message.answer.assert_called_once()
    args = mock_message.answer.call_args[0][0]
    assert "VideoGrabberBot Help" in args
    assert "Available commands" in args
    assert "/help" in args
    assert "/start" in args
    assert "/invite" in args
    assert "/cancel" in args


@pytest.mark.asyncio
async def test_help_command_unauthorized_user(secure_command_db, unauthorized_user, mock_message):
    """Test /help command with real unauthorized user."""
    # Do NOT add user to database
    mock_message.from_user = unauthorized_user

    # Call help command - uses real is_user_authorized
    await command_help(mock_message)

    # Verify access restricted message was sent
    mock_message.answer.assert_called_once()
    args = mock_message.answer.call_args[0][0]
    assert "Access Restricted" in args


@pytest.mark.asyncio
async def test_start_command_authorized_user(secure_command_db, authorized_user, mock_message):
    """Test /start command with authorized user."""
    # Add user to database
    await add_user(authorized_user.id, authorized_user.username, authorized_user.id)

    mock_message.from_user = authorized_user
    mock_message.text = "/start"

    await command_start(mock_message)

    # Should show welcome message for authorized user
    mock_message.answer.assert_called_once()
    args = mock_message.answer.call_args[0][0]
    assert "Welcome" in args or "Hello" in args


@pytest.mark.asyncio
async def test_start_command_unauthorized_user(secure_command_db, unauthorized_user, mock_message):
    """Test /start command with unauthorized user."""
    # Do not add user to database
    mock_message.from_user = unauthorized_user
    mock_message.text = "/start"

    await command_start(mock_message)

    # Should show access restricted message
    mock_message.answer.assert_called_once()
    args = mock_message.answer.call_args[0][0]
    assert "Access Restricted" in args


@pytest.mark.asyncio
async def test_cancel_command_authorized_user(secure_command_db, authorized_user, mock_message, mocker):
    """Test /cancel command with authorized user."""
    # Add user to database
    await add_user(authorized_user.id, authorized_user.username, authorized_user.id)

    mock_message.from_user = authorized_user
    mock_message.chat.id = authorized_user.id

    # Mock queue operations
    mock_queue = mocker.patch("bot.services.queue.download_queue")
    mock_queue.is_user_in_queue = mocker.MagicMock(return_value=True)
    mock_queue.clear_user_tasks = mocker.AsyncMock(return_value=2)

    await command_cancel(mock_message)

    # Should process cancel for authorized user
    mock_message.answer.assert_called()
    mock_queue.clear_user_tasks.assert_called_once_with(authorized_user.id)


@pytest.mark.asyncio
async def test_cancel_command_unauthorized_user(secure_command_db, unauthorized_user, mock_message, mocker):
    """Test /cancel command with unauthorized user."""
    # Do not add user to database
    mock_message.from_user = unauthorized_user

    mock_queue = mocker.patch("bot.services.queue.download_queue")
    await command_cancel(mock_message)

    # Should not process cancel for unauthorized user
    mock_message.answer.assert_called_once()
    args = mock_message.answer.call_args[0][0]
    assert "Access Restricted" in args or "access restricted" in args.lower()

    # Queue should not be called
    mock_queue.clear_user_tasks.assert_not_called()


@pytest.mark.asyncio
async def test_invite_command_admin_user(secure_command_db, mock_message, mocker):
    """Test /invite command with admin user."""
    # Create admin user
    admin_user = mocker.MagicMock(spec=User)
    admin_user.id = 987654321
    admin_user.username = "admin"

    # Add admin to database
    await add_user(admin_user.id, admin_user.username, admin_user.id)

    mock_message.from_user = admin_user

    # Mock admin configuration and bot.get_me()
    mock_bot_me = mocker.MagicMock()
    mock_bot_me.username = "test_bot"
    mock_message.bot.get_me = mocker.AsyncMock(return_value=mock_bot_me)

    mocker.patch("bot.handlers.commands.ADMIN_USER_ID", admin_user.id)
    await command_invite(mock_message)

    # Should create invite for admin
    mock_message.answer.assert_called()
    args = mock_message.answer.call_args[0][0]
    assert "invite" in args.lower()


@pytest.mark.asyncio
async def test_invite_command_non_admin_user(secure_command_db, authorized_user, mock_message, mocker):
    """Test /invite command with non-admin user."""
    # Add regular user to database
    await add_user(authorized_user.id, authorized_user.username, authorized_user.id)

    mock_message.from_user = authorized_user

    # Mock bot.get_me()
    mock_bot_me = mocker.MagicMock()
    mock_bot_me.username = "test_bot"
    mock_message.bot.get_me = mocker.AsyncMock(return_value=mock_bot_me)

    # Mock different admin ID
    mocker.patch("bot.handlers.commands.ADMIN_USER_ID", 999999999)
    await command_invite(mock_message)

    # Should create invite for authorized user (invite is not admin-only)
    mock_message.answer.assert_called()
    args = mock_message.answer.call_args[0][0]
    assert "invite" in args.lower() and "generated" in args.lower()


@pytest.mark.asyncio
async def test_adduser_command_admin_user(secure_command_db, mock_message, mocker):
    """Test /adduser command with admin user."""
    # Create admin user
    admin_user = mocker.MagicMock(spec=User)
    admin_user.id = 987654321
    admin_user.username = "admin"

    # Add admin to database
    await add_user(admin_user.id, admin_user.username, admin_user.id)

    mock_message.from_user = admin_user
    mock_message.text = "/adduser 123456789"

    # Mock admin configuration
    mocker.patch("bot.handlers.commands.ADMIN_USER_ID", admin_user.id)
    await command_adduser(mock_message)

    # Should add user for admin
    mock_message.answer.assert_called()
    args = mock_message.answer.call_args[0][0]
    assert "User Added" in args or "added" in args.lower()


@pytest.mark.asyncio
async def test_adduser_command_non_admin_user(secure_command_db, authorized_user, mock_message, mocker):
    """Test /adduser command with non-admin user."""
    # Add regular user to database
    await add_user(authorized_user.id, authorized_user.username, authorized_user.id)

    mock_message.from_user = authorized_user
    mock_message.text = "/adduser 123456789"

    # Mock different admin ID
    mocker.patch("bot.handlers.commands.ADMIN_USER_ID", 999999999)
    await command_adduser(mock_message)

    # Should reject non-admin user
    mock_message.answer.assert_called()
    args = mock_message.answer.call_args[0][0]
    assert "Admin Only" in args or "admin" in args.lower()


@pytest.mark.asyncio
async def test_adduser_command_unauthorized_user(secure_command_db, unauthorized_user, mock_message):
    """Test /adduser command with unauthorized user."""
    # Do not add user to database
    mock_message.from_user = unauthorized_user
    mock_message.text = "/adduser 123456789"

    await command_adduser(mock_message)

    # Should show admin only message for unauthorized user (adduser only checks admin, not authorization)
    mock_message.answer.assert_called()
    args = mock_message.answer.call_args[0][0]
    assert "Admin Only" in args or "admin" in args.lower()


@pytest.mark.asyncio
async def test_command_authorization_consistency(secure_command_db, authorized_user, mock_message):
    """Test that authorization is consistent across multiple command calls."""
    # Add user to database
    await add_user(authorized_user.id, authorized_user.username, authorized_user.id)

    mock_message.from_user = authorized_user

    # Test help command
    await command_help(mock_message)
    mock_message.answer.assert_called()
    help_args = mock_message.answer.call_args[0][0]
    assert "VideoGrabberBot Help" in help_args

    # Reset mock
    mock_message.answer.reset_mock()

    # Test start command
    mock_message.text = "/start"
    await command_start(mock_message)
    mock_message.answer.assert_called()
    start_args = mock_message.answer.call_args[0][0]
    assert "Welcome" in start_args or "Hello" in start_args

    # Both should succeed with same authorization


@pytest.mark.asyncio
async def test_deactivated_user_loses_access(secure_command_db, authorized_user, mock_message):
    """Test that deactivated users immediately lose command access."""
    from bot.utils.db import deactivate_user

    # Add user to database
    await add_user(authorized_user.id, authorized_user.username, authorized_user.id)

    mock_message.from_user = authorized_user

    # Verify user has access initially
    await command_help(mock_message)
    mock_message.answer.assert_called()
    help_args = mock_message.answer.call_args[0][0]
    assert "VideoGrabberBot Help" in help_args

    # Deactivate user
    await deactivate_user(authorized_user.id)

    # Reset mock
    mock_message.answer.reset_mock()

    # User should now be denied access
    await command_help(mock_message)
    mock_message.answer.assert_called()
    restricted_args = mock_message.answer.call_args[0][0]
    assert "Access Restricted" in restricted_args
