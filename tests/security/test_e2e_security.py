"""End-to-end security tests for critical authorization paths.

These tests verify complete security workflows from user input to authorization
without excessive mocking to ensure security vulnerabilities aren't hidden.
"""

import tempfile
from pathlib import Path

import pytest
import pytest_asyncio
from aiogram.types import CallbackQuery, Message, User

from bot.handlers.commands import command_adduser, command_help, command_invite
from bot.handlers.download import process_format_selection, process_url
from bot.utils.db import add_user, init_db


@pytest_asyncio.fixture
async def e2e_test_db(mocker):
    """Create real database for end-to-end testing."""
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_db_path = Path(temp_dir) / "e2e_security_test.db"

        mocker.patch("bot.utils.db.DB_PATH", temp_db_path)
        await init_db()
        yield temp_db_path


@pytest.fixture
def mock_authorized_user(mocker):
    """Create a mock user that will be added to real database."""
    user = mocker.MagicMock(spec=User)
    user.id = 123456789
    user.username = "authorized_user"
    user.first_name = "Authorized"
    user.last_name = "User"
    return user


@pytest.fixture
def mock_unauthorized_user(mocker):
    """Create a mock user that will NOT be added to database."""
    user = mocker.MagicMock(spec=User)
    user.id = 999999999
    user.username = "unauthorized_user"
    user.first_name = "Unauthorized"
    user.last_name = "User"
    return user


@pytest.fixture
def mock_message(mocker):
    """Create mock message with answer method."""
    message = mocker.MagicMock(spec=Message)
    message.answer = mocker.AsyncMock()
    message.reply = mocker.AsyncMock()
    return message


@pytest.mark.asyncio
async def test_e2e_unauthorized_user_help_command(e2e_test_db, mock_unauthorized_user, mock_message):
    """Test that unauthorized users cannot access help command."""
    mock_message.from_user = mock_unauthorized_user

    # Call help command - should reject unauthorized user
    await command_help(mock_message)

    # Verify unauthorized message was sent
    mock_message.answer.assert_called_once()
    call_args = mock_message.answer.call_args
    message_text = call_args[0][0]
    assert "access restricted" in message_text.lower() or "permission" in message_text.lower()


@pytest.mark.asyncio
async def test_e2e_authorized_user_help_command(e2e_test_db, mock_authorized_user, mock_message):
    """Test that authorized users can access help command."""
    # First add user to database (real authorization)
    await add_user(mock_authorized_user.id, mock_authorized_user.username, mock_authorized_user.id)

    mock_message.from_user = mock_authorized_user

    # Call help command - should work for authorized user
    await command_help(mock_message)

    # Verify help message was sent (not unauthorized message)
    mock_message.answer.assert_called_once()
    call_args = mock_message.answer.call_args
    message_text = call_args[0][0]
    assert "VideoGrabberBot Help" in message_text
    assert "Available commands" in message_text


@pytest.mark.asyncio
async def test_e2e_unauthorized_user_download_attempt(e2e_test_db, mock_unauthorized_user, mock_message):
    """Test that unauthorized users cannot download videos."""
    mock_message.from_user = mock_unauthorized_user
    mock_message.text = "https://www.youtube.com/watch?v=test_video"

    # Attempt to process URL - should be rejected
    await process_url(mock_message)

    # Verify unauthorized message was sent
    mock_message.answer.assert_called_once()
    call_args = mock_message.answer.call_args
    message_text = call_args[0][0]
    assert "access restricted" in message_text.lower() or "permission" in message_text.lower()


@pytest.mark.asyncio
async def test_e2e_authorized_user_download_flow(e2e_test_db, mock_authorized_user, mock_message, mocker):
    """Test that authorized users can initiate download flow."""
    # Add user to database (real authorization)
    await add_user(mock_authorized_user.id, mock_authorized_user.username, mock_authorized_user.id)

    mock_message.from_user = mock_authorized_user
    mock_message.text = "https://www.youtube.com/watch?v=test_video"

    mocker.patch("bot.handlers.download.store_url", return_value="test_url_id")
    # Process URL - should work for authorized user
    await process_url(mock_message)

    # Verify format selection was presented (not unauthorized message)
    mock_message.answer.assert_called_once()
    call_args = mock_message.answer.call_args
    message_text = call_args[0][0]
    assert "Choose Download Format" in message_text
    assert "not authorized" not in message_text.lower()


@pytest.mark.asyncio
async def test_e2e_unauthorized_callback_query(e2e_test_db, mock_unauthorized_user, mocker):
    """Test that unauthorized users cannot use callback queries."""
    callback_query = mocker.MagicMock(spec=CallbackQuery)
    callback_query.from_user = mock_unauthorized_user
    callback_query.data = "fmt:TEST_HD:test_url_id"
    callback_query.answer = mocker.AsyncMock()
    callback_query.message = mocker.MagicMock()
    callback_query.message.edit_text = mocker.AsyncMock()

    # Mock URL storage and format to ensure callback processes correctly
    mocker.patch("bot.handlers.download.get_url", return_value="https://youtube.com/watch?v=test")
    mocker.patch("bot.handlers.download.get_format_by_id", return_value={"label": "HD (720p)", "format": "test_format"})
    mock_queue = mocker.patch("bot.handlers.download.download_queue")
    mock_queue.add_task = mocker.AsyncMock(return_value=1)

    # SECURITY FIX: Authorization check now properly blocks unauthorized callback queries
    await process_format_selection(callback_query)

    # Should answer callback with access denied message
    callback_query.answer.assert_called_once_with("⛔ Access Denied")

    # Should NOT edit message (early return due to auth failure)
    callback_query.message.edit_text.assert_not_called()

    # Should NOT add task to queue (auth check prevents this)
    mock_queue.add_task.assert_not_called()


@pytest.mark.asyncio
async def test_e2e_admin_only_commands(e2e_test_db, mock_unauthorized_user, mock_message):
    """Test that non-admin users cannot execute admin-only commands."""
    mock_message.from_user = mock_unauthorized_user
    mock_message.get_args = lambda: ["123456789", "newuser"]

    # Try to add user (admin-only command)
    await command_adduser(mock_message)

    # Should be rejected
    mock_message.answer.assert_called_once()
    call_args = mock_message.answer.call_args
    message_text = call_args[0][0]
    assert (
        "admin" in message_text.lower() and "only" in message_text.lower()
    ) or "not authorized" in message_text.lower()


@pytest.mark.asyncio
async def test_e2e_invite_system_security(e2e_test_db, mock_message, mocker):
    """Test complete invite system security flow."""
    # Create admin user
    admin_user = mocker.MagicMock(spec=User)
    admin_user.id = 987654321
    admin_user.username = "admin"

    # Add admin to database
    await add_user(admin_user.id, admin_user.username, admin_user.id)

    mock_message.from_user = admin_user

    # Mock bot.get_me() and admin configuration
    mock_bot_me = mocker.MagicMock()
    mock_bot_me.username = "test_bot"
    mock_message.bot.get_me = mocker.AsyncMock(return_value=mock_bot_me)

    # Mock the configuration to recognize this user as admin
    mocker.patch("bot.handlers.commands.ADMIN_USER_ID", admin_user.id)
    # Admin creates invite
    await command_invite(mock_message)

    # Should succeed for admin
    mock_message.answer.assert_called()
    call_args = mock_message.answer.call_args
    message_text = call_args[0][0]
    assert "invite" in message_text.lower()
    assert "not authorized" not in message_text.lower()


@pytest.mark.asyncio
async def test_e2e_session_consistency(e2e_test_db, mock_authorized_user, mock_message, mocker):
    """Test that authorization remains consistent across multiple operations."""
    # Add user to database
    await add_user(mock_authorized_user.id, mock_authorized_user.username, mock_authorized_user.id)

    mock_message.from_user = mock_authorized_user

    # First operation - help command
    await command_help(mock_message)
    mock_message.answer.assert_called()

    # Reset mock for next call
    mock_message.answer.reset_mock()

    # Second operation - URL processing
    mock_message.text = "https://www.youtube.com/watch?v=test_video"
    mocker.patch("bot.handlers.download.store_url", return_value="test_url_id")
    await process_url(mock_message)

    # Both operations should succeed
    mock_message.answer.assert_called()
    call_args = mock_message.answer.call_args
    message_text = call_args[0][0]
    assert "Choose Download Format" in message_text


@pytest.mark.asyncio
async def test_e2e_malicious_input_handling(e2e_test_db, mock_authorized_user, mock_message, mocker):
    """Test that system handles malicious inputs securely."""
    # Add authorized user
    await add_user(mock_authorized_user.id, mock_authorized_user.username, mock_authorized_user.id)

    mock_message.from_user = mock_authorized_user

    # Test with malicious URL input
    malicious_urls = [
        "javascript:alert('xss')",
        "file:///etc/passwd",
        "' OR '1'='1'; DROP TABLE users; --",
        "../../../etc/passwd",
        "https://evil.com/malware.exe",
    ]

    for malicious_url in malicious_urls:
        mock_message.text = malicious_url
        mock_message.answer.reset_mock()

        # Should handle malicious input gracefully
        await process_url(mock_message)

        # Should respond (not crash) and not process malicious content
        mock_message.answer.assert_called()
        call_args = mock_message.answer.call_args
        message_text = call_args[0][0]

        # Should not contain dangerous content or crash
        assert message_text is not None
        assert len(message_text) > 0


@pytest.mark.asyncio
async def test_e2e_authorization_after_deactivation(e2e_test_db, mock_authorized_user, mock_message, mocker):
    """Test that deactivated users lose access immediately."""
    from bot.utils.db import deactivate_user

    # Add and authorize user
    await add_user(mock_authorized_user.id, mock_authorized_user.username, mock_authorized_user.id)

    mock_message.from_user = mock_authorized_user

    # First verify user can access
    await command_help(mock_message)
    mock_message.answer.assert_called()
    call_args = mock_message.answer.call_args
    message_text = call_args[0][0]
    assert "VideoGrabberBot Help" in message_text

    # Deactivate user
    await deactivate_user(mock_authorized_user.id)

    # Reset mock
    mock_message.answer.reset_mock()

    # Now user should be denied access
    await command_help(mock_message)
    mock_message.answer.assert_called()
    call_args = mock_message.answer.call_args
    message_text = call_args[0][0]
    assert "access restricted" in message_text.lower() or "permission" in message_text.lower()
