"""Tests for the database module."""

import pytest

from bot.utils.db import (
    add_user,
    create_invite,
    deactivate_user,
    get_all_users,
    is_user_authorized,
    use_invite,
)

TEST_USER_ID = 123456789
ADDED_BY_USER_ID = 987654321


@pytest.fixture
def db_connection_error(mocker):
    """Mock aiosqlite.connect to raise a database connection error."""
    mocker.patch("aiosqlite.connect", side_effect=Exception("Database error"))


@pytest.mark.asyncio
async def test_add_user(temp_db):
    """Test adding users to the database."""
    result1 = await add_user(TEST_USER_ID, "testuser", ADDED_BY_USER_ID)
    assert result1 is True

    result2 = await add_user(TEST_USER_ID, "testuser_updated", ADDED_BY_USER_ID)
    assert result2 is False

    is_auth = await is_user_authorized(TEST_USER_ID)
    assert is_auth is True


@pytest.mark.asyncio
async def test_add_user_exception(temp_db, mocker):
    """Test handling exception when adding a user."""
    mocker.patch("aiosqlite.connect", side_effect=Exception("Database error"))
    success = await add_user(TEST_USER_ID, "testuser", ADDED_BY_USER_ID)
    assert success is False


@pytest.mark.asyncio
async def test_get_all_users(temp_db):
    """Test retrieving all users."""
    await add_user(111, "user1", 999)
    await add_user(222, "user2", 999)
    await add_user(333, "user3", 999)

    users = await get_all_users()

    assert len(users) == 4  # 3 added users + 1 admin user created by init_db
    user_ids = [user["id"] for user in users]
    assert 111 in user_ids
    assert 222 in user_ids
    assert 333 in user_ids


@pytest.mark.asyncio
async def test_get_all_users_exception(temp_db, mocker):
    """Test exception handling when retrieving users."""
    mocker.patch("aiosqlite.connect", side_effect=Exception("Database error"))
    users = await get_all_users()
    assert users == []


@pytest.mark.asyncio
async def test_deactivate_user(temp_db):
    """Test deactivating a user."""
    await add_user(TEST_USER_ID, "testuser", ADDED_BY_USER_ID)

    assert await is_user_authorized(TEST_USER_ID) is True

    success = await deactivate_user(TEST_USER_ID)
    assert success is True

    assert await is_user_authorized(TEST_USER_ID) is False


@pytest.mark.asyncio
async def test_deactivate_user_exception(temp_db, mocker):
    """Test exception handling when deactivating a user."""
    mocker.patch("aiosqlite.connect", side_effect=Exception("Database error"))
    success = await deactivate_user(TEST_USER_ID)
    assert success is False


@pytest.mark.asyncio
async def test_is_user_authorized_exception(temp_db, mocker):
    """Test exception handling when checking if a user is authorized."""
    mocker.patch("aiosqlite.connect", side_effect=Exception("Database error"))
    is_auth = await is_user_authorized(TEST_USER_ID)
    assert is_auth is False


@pytest.mark.asyncio
async def test_invite_create_success(mocker):
    """Test creating an invite successfully."""
    mock_connect = mocker.patch("aiosqlite.connect")
    mocker.patch("uuid.uuid4", return_value="test-uuid")

    mock_cursor = mocker.AsyncMock()
    mock_conn = mocker.AsyncMock()
    mock_conn.execute = mocker.AsyncMock(return_value=mock_cursor)
    mock_conn.__aenter__.return_value = mock_conn
    mock_connect.return_value = mock_conn

    invite_id = await create_invite(ADDED_BY_USER_ID)
    assert invite_id == "test-uuid"

    mock_conn.execute.assert_called_once()
    mock_conn.commit.assert_called_once()


@pytest.mark.asyncio
async def test_invite_create_db_exception(db_connection_error):
    """Test exception handling when creating an invite."""
    invite_id = await create_invite(ADDED_BY_USER_ID)
    assert invite_id is None


@pytest.mark.asyncio
async def test_use_invite_valid_new_user(mocker):
    """Test using a valid invite for a new user who doesn't exist yet."""
    mock_connect = mocker.patch("aiosqlite.connect")

    invite_cursor = mocker.AsyncMock()
    invite_cursor.fetchone.return_value = ["test-invite-id"]

    user_cursor = mocker.AsyncMock()
    user_cursor.fetchone.return_value = None

    mock_conn = mocker.AsyncMock()
    mock_conn.execute = mocker.AsyncMock(
        side_effect=[
            invite_cursor,       # SELECT FROM invites
            mocker.AsyncMock(),  # UPDATE invites SET used_by
            user_cursor,         # SELECT FROM users
            mocker.AsyncMock(),  # INSERT INTO users
        ]
    )
    mock_conn.__aenter__.return_value = mock_conn
    mock_connect.return_value = mock_conn

    success = await use_invite("test-invite-id", TEST_USER_ID)
    assert success is True
    assert mock_conn.execute.call_count == 4
    mock_conn.commit.assert_called_once()


@pytest.mark.asyncio
async def test_use_invite_invalid(mocker):
    """Test using an invite that doesn't exist in the database."""
    mock_connect = mocker.patch("aiosqlite.connect")

    no_invite_cursor = mocker.AsyncMock()
    no_invite_cursor.fetchone.return_value = None

    mock_conn = mocker.AsyncMock()
    mock_conn.execute = mocker.AsyncMock(return_value=no_invite_cursor)
    mock_conn.__aenter__.return_value = mock_conn
    mock_connect.return_value = mock_conn

    success = await use_invite("invalid-invite", TEST_USER_ID)

    assert success is False
    assert mock_conn.execute.call_count == 1
    mock_conn.commit.assert_not_called()


@pytest.mark.asyncio
async def test_use_invite_db_exception(db_connection_error):
    """Test exception handling when using an invite."""
    success = await use_invite("test-invite-id", TEST_USER_ID)
    assert success is False


@pytest.mark.asyncio
async def test_error_handling(temp_db):
    """Test error handling in database operations."""
    success = await add_user("invalid_id", "testuser", ADDED_BY_USER_ID)
    assert success is False

    success = await use_invite("non_existent_invite", TEST_USER_ID)
    assert success is False
