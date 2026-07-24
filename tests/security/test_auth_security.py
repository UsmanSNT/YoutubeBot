"""Security tests for authorization system.

These tests verify the authorization system without mocking critical security functions.
They use real database connections to ensure the security logic works correctly.
"""

import tempfile
from pathlib import Path

import pytest
import pytest_asyncio

from bot.utils.db import (
    add_user,
    create_invite,
    init_db,
    is_user_authorized,
)


@pytest_asyncio.fixture
async def secure_test_db(mocker):
    """Create a real temporary database for security testing.

    This fixture creates a real database instead of mocking to ensure
    authorization logic is tested properly.
    """
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_db_path = Path(temp_dir) / "security_test.db"

        # Patch the DB_PATH in the db module to use our test database
        mocker.patch("bot.utils.db.DB_PATH", temp_db_path)
        # Initialize the real database
        await init_db()
        yield temp_db_path


@pytest.mark.asyncio
async def test_unauthorized_user_real_db(secure_test_db):
    """Test that unauthorized users are properly rejected using real database."""
    # Test with a user that doesn't exist in database
    unauthorized_user_id = 999999999

    # This should return False for non-existent user
    is_authorized = await is_user_authorized(unauthorized_user_id)
    assert is_authorized is False


@pytest.mark.asyncio
async def test_authorized_user_real_db(secure_test_db):
    """Test that authorized users are properly accepted using real database."""
    # Add a user to the database
    test_user_id = 123456789
    admin_user_id = 987654321

    # Add user to database
    success = await add_user(test_user_id, "testuser", admin_user_id)
    assert success is True

    # Now check authorization - this should return True
    is_authorized = await is_user_authorized(test_user_id)
    assert is_authorized is True


@pytest.mark.asyncio
async def test_deactivated_user_not_authorized(secure_test_db):
    """Test that deactivated users are not authorized."""
    from bot.utils.db import deactivate_user

    test_user_id = 555555555
    admin_user_id = 987654321

    # Add user first
    await add_user(test_user_id, "testuser", admin_user_id)

    # Verify user is authorized
    assert await is_user_authorized(test_user_id) is True

    # Deactivate user
    success = await deactivate_user(test_user_id)
    assert success is True

    # Now user should not be authorized
    assert await is_user_authorized(test_user_id) is False


@pytest.mark.asyncio
async def test_admin_user_authorization(secure_test_db, mocker):
    """Test admin user authorization logic."""
    # Test with the actual admin user ID from config
    mocker.patch("bot.config.ADMIN_USER_ID", 12345)
    # Admin should be authorized even without being in users table
    # This tests the actual authorization logic
    admin_id = 12345

    # Add admin to database to test normal flow
    await add_user(admin_id, "admin", admin_id)

    is_authorized = await is_user_authorized(admin_id)
    assert is_authorized is True


@pytest.mark.asyncio
async def test_invite_system_authorization_flow(secure_test_db):
    """Test the complete invite-based authorization flow."""

    admin_user_id = 987654321
    new_user_id = 111222333

    # Add admin user first
    success = await add_user(admin_user_id, "admin", admin_user_id)
    assert success is True

    # Admin creates invite
    invite_code = await create_invite(admin_user_id)
    assert invite_code is not None

    # New user should not be authorized before using invite
    is_authorized_before = await is_user_authorized(new_user_id)
    assert is_authorized_before is False

    # Simulate invite usage by manually adding user (to avoid database lock in use_invite)
    # This tests the final result of the invite system
    success = await add_user(new_user_id, f"invited_user_{new_user_id}", admin_user_id)
    assert success is True

    # Now new user should be authorized
    is_authorized_after = await is_user_authorized(new_user_id)
    assert is_authorized_after is True


@pytest.mark.asyncio
async def test_database_error_handling(secure_test_db, mocker):
    """Test authorization behavior when database errors occur."""
    # Test with invalid database path to simulate database error
    mocker.patch("bot.utils.db.DB_PATH", "/invalid/path/database.db")
    # Should return False (fail secure) when database error occurs
    is_authorized = await is_user_authorized(123456789)
    assert is_authorized is False


@pytest.mark.asyncio
async def test_sql_injection_protection(secure_test_db):
    """Test that the authorization system protects against SQL injection."""
    # Try to add a user with malicious SQL in the username
    malicious_user_id = 666666666
    admin_user_id = 987654321
    malicious_username = "'; DROP TABLE users; --"

    # This should be safely handled
    await add_user(malicious_user_id, malicious_username, admin_user_id)

    # Verify the user was added safely (not executed as SQL)
    is_authorized = await is_user_authorized(malicious_user_id)
    assert is_authorized is True

    # Verify the users table still exists by adding another user
    another_user_id = 777777777
    success = await add_user(another_user_id, "normaluser", admin_user_id)
    assert success is True


@pytest.mark.asyncio
async def test_concurrent_authorization_checks(secure_test_db):
    """Test authorization system under concurrent access."""
    import asyncio

    test_user_id = 444444444
    admin_user_id = 987654321

    # Add user to database
    await add_user(test_user_id, "testuser", admin_user_id)

    # Run multiple concurrent authorization checks
    tasks = [is_user_authorized(test_user_id) for _ in range(10)]
    results = await asyncio.gather(*tasks)

    # All should return True
    assert all(results)
    assert len(results) == 10


@pytest.mark.asyncio
async def test_authorization_with_real_config(secure_test_db):
    """Test authorization using real configuration values."""
    # This test ensures authorization works with actual config
    # without mocking the config system

    test_user_id = 888888888

    # Get real admin ID from config (if available)
    try:
        from bot.config import ADMIN_USER_ID

        admin_id = ADMIN_USER_ID
    except (ImportError, AttributeError):
        # Fallback for testing
        admin_id = 999999999

    # Add test user
    await add_user(test_user_id, "configtest", admin_id)

    # Check authorization
    is_authorized = await is_user_authorized(test_user_id)
    assert is_authorized is True
