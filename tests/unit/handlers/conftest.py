"""Shared fixtures for unit handler tests."""

import pytest


@pytest.fixture
def make_message_mock(mocker):
    """Factory fixture for creating mock message/user pairs.

    Returns:
        Factory function that creates a mock Message with an attached mock User
    """
    from aiogram.types import Message, User

    def _factory(user_id: int = 123456, text: str = "") -> object:
        mock_user = mocker.MagicMock(spec=User)
        mock_user.id = user_id
        mock_user.username = f"user_{user_id}"
        mock_message = mocker.MagicMock(spec=Message)
        mock_message.answer = mocker.AsyncMock()
        mock_message.from_user = mock_user
        mock_message.chat = mocker.MagicMock(id=user_id)
        mock_message.text = text
        return mock_message

    return _factory
