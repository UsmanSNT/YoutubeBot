"""Integration tests for command interactions."""

import pytest

from bot.handlers.commands import (
    command_adduser,
    command_cancel,
    command_help,
    command_invite,
    command_start,
)
from bot.services.queue import DownloadTask, download_queue


@pytest.mark.asyncio
@pytest.mark.integration
async def test_command_interaction_flow(integration_setup, mock_message, authorized_user, mock_command_system):
    """Test the flow of a user interacting with multiple commands."""
    # User starts bot interaction with /start
    mock_message.text = "/start"
    await command_start(mock_message)

    # Verify welcome message
    args = mock_message.answer.call_args[0][0]
    assert "Welcome to VideoGrabberBot" in args
    mock_message.answer.reset_mock()

    # User asks for help
    mock_message.text = "/help"
    await command_help(mock_message)

    # Verify help message
    args = mock_message.answer.call_args[0][0]
    assert "VideoGrabberBot Help" in args
    assert "Available commands" in args
    mock_message.answer.reset_mock()

    # User generates an invite link
    mock_message.text = "/invite"
    await command_invite(mock_message)

    # Verify invite link was generated
    args = mock_message.answer.call_args[0][0]
    assert "Invite Link Generated" in args
    assert "https://t.me/test_bot?start=test_invite" in args
    mock_message.answer.reset_mock()


@pytest.mark.asyncio
@pytest.mark.integration
async def test_admin_user_commands(integration_setup, mock_message, mock_command_system):
    """Test admin-specific commands."""
    # Set up message as coming from admin user
    from bot.config import ADMIN_USER_ID

    mock_message.from_user.id = ADMIN_USER_ID

    # Admin adds a new user
    mock_message.text = "/adduser 987654321"
    await command_adduser(mock_message)

    # Verify confirmation message
    args = mock_message.answer.call_args[0][0]
    assert "User Added" in args
    assert "987654321" in args
    mock_message.answer.reset_mock()

    # Try adding a user that already exists
    mock_message.text = "/adduser 987654321"

    # Configure the mock to return False for duplicate user
    mock_command_system["add_user_success"].return_value = False
    await command_adduser(mock_message)

    # Verify message about existing user
    args = mock_message.answer.call_args[0][0]
    assert "User Already Exists" in args
    mock_message.answer.reset_mock()


@pytest.mark.asyncio
@pytest.mark.integration
async def test_cancel_command_integration(integration_setup, mock_message, authorized_user):
    """Test the /cancel command with active downloads in the queue."""
    # Set up message
    mock_message.from_user = authorized_user
    mock_message.chat.id = authorized_user.id

    # Add some tasks to the queue
    task1 = DownloadTask(
        chat_id=authorized_user.id,
        url="https://www.youtube.com/watch?v=test1",
        format_string="best[height<=720]",
    )

    task2 = DownloadTask(
        chat_id=authorized_user.id,
        url="https://www.youtube.com/watch?v=test2",
        format_string="best[height<=720]",
    )

    # Add tasks to queue without starting worker (for test)
    await download_queue.queue.put(task1)
    await download_queue.queue.put(task2)
    download_queue._queue_items.append(task1)
    download_queue._queue_items.append(task2)

    # Verify tasks were added
    assert download_queue.queue.qsize() == 2
    assert download_queue.is_user_in_queue(authorized_user.id)

    # User runs /cancel command
    mock_message.text = "/cancel"
    await command_cancel(mock_message)

    # Verify cancel confirmation
    args = mock_message.answer.call_args[0][0]
    assert "Downloads Cancelled" in args
    assert "2 download" in args  # Should say 2 downloads

    # Verify queue is empty
    assert download_queue.queue.empty()
    assert not download_queue.is_user_in_queue(authorized_user.id)


@pytest.mark.asyncio
@pytest.mark.integration
async def test_invite_workflow(integration_setup, mock_message, mock_bot, mock_command_system):
    """Test the full invite workflow - creating and using an invite."""
    # Admin/authorized user creates an invite
    mock_message.text = "/invite"
    await command_invite(mock_message)

    # Verify invite was created and contains the invite code
    args = mock_message.answer.call_args[0][0]
    assert "Invite Link Generated" in args
    assert "test_invite" in args

    # Now we can test that an authorized user gets proper welcome message
    # Create a new message for clarity
    from unittest.mock import AsyncMock, MagicMock

    user_message = MagicMock()
    user_message.from_user = mock_message.from_user  # Already authorized
    user_message.text = "/start"
    user_message.answer = AsyncMock()

    # Just send a start command
    await command_start(user_message)

    # Verify welcome message
    args = user_message.answer.call_args[0][0]
    assert "Welcome to VideoGrabberBot" in args

    # Test that the help command works for authorized user
    user_message.text = "/help"
    user_message.answer.reset_mock()
    await command_help(user_message)

    # Verify help message
    user_message.answer.assert_called()
    args = user_message.answer.call_args[0][0]
    assert "VideoGrabberBot Help" in args
