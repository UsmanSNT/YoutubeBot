"""Database module for VideoGrabberBot."""

import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

import aiosqlite
from loguru import logger

from bot.config import DB_PATH


def get_db_connection() -> aiosqlite.Connection:
    """Get database connection with timeout settings."""
    return aiosqlite.connect(DB_PATH, timeout=20.0)


async def init_db() -> None:
    """Initialize the database with required tables."""
    async with aiosqlite.connect(DB_PATH) as db:
        # Enable WAL mode for better concurrency
        await db.execute("PRAGMA journal_mode=WAL")
        await db.execute("PRAGMA synchronous=NORMAL")
        await db.execute("PRAGMA temp_store=memory")
        await db.execute("PRAGMA mmap_size=268435456")  # 256MB
        # Create users table
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY,
                username TEXT,
                added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                added_by INTEGER,
                is_active BOOLEAN DEFAULT TRUE
            )
            """
        )

        # Create invites table
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS invites (
                id TEXT PRIMARY KEY,
                created_by INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                used_by INTEGER,
                used_at TIMESTAMP,
                is_active BOOLEAN DEFAULT TRUE
            )
            """
        )

        # Create settings table for admin configuration
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )

        # Add admin user if not exists
        from bot.config import ADMIN_USER_ID

        await db.execute(
            """
            INSERT OR IGNORE INTO users (id, username, added_by, is_active)
            VALUES (?, ?, ?, TRUE)
            """,
            (ADMIN_USER_ID, "admin", 0),  # 0 means system added
        )

        await db.commit()
        logger.info("Database initialized")


async def add_user(
    user_id: int,
    username: Optional[str] = None,
    added_by: Optional[int] = None,
) -> bool:
    """
    Add a new user to the database.

    Args:
        user_id: Telegram user ID
        username: Telegram username (without @)
        added_by: ID of the user who added this user

    Returns:
        bool: True if user was added successfully, False if user already exists
    """
    try:
        async with get_db_connection() as db:
            # Check if user already exists
            cursor = await db.execute("SELECT id FROM users WHERE id = ?", (user_id,))
            existing_user = await cursor.fetchone()

            if existing_user:
                # User exists, update their info
                await db.execute(
                    "UPDATE users SET username = ?, is_active = TRUE WHERE id = ?",
                    (username, user_id),
                )
                logger.info(f"Updated existing user: {user_id} ({username})")
                user_added = False
            else:
                # Add new user
                await db.execute(
                    "INSERT INTO users (id, username, added_by) VALUES (?, ?, ?)",
                    (user_id, username, added_by),
                )
                logger.info(f"Added new user: {user_id} ({username})")
                user_added = True

            await db.commit()
            return user_added
    except Exception as e:
        logger.error(f"Error adding user {user_id}: {e}")
        return False


async def is_user_authorized(user_id: int) -> bool:
    """
    Check if a user is authorized to use the bot.

    Args:
        user_id: Telegram user ID

    Returns:
        bool: True if user is authorized, False otherwise
    """
    try:
        async with get_db_connection() as db:
            cursor = await db.execute(
                "SELECT id FROM users WHERE id = ? AND is_active = TRUE",
                (user_id,),
            )
            user = await cursor.fetchone()
            return user is not None
    except Exception as e:
        logger.error(f"Error checking user authorization {user_id}: {e}")
        return False


async def create_invite(created_by: int) -> Optional[str]:
    """
    Create a new invite link.

    Args:
        created_by: Telegram user ID of the admin creating the invite

    Returns:
        str: Invite code or None if failed
    """
    try:
        invite_id = str(uuid.uuid4())
    except Exception as e:
        logger.error(f"Error generating invite ID: {e}")
        return None

    try:
        async with get_db_connection() as db:
            await db.execute(
                "INSERT INTO invites (id, created_by) VALUES (?, ?)",
                (invite_id, created_by),
            )
            await db.commit()
            logger.info(f"Created invite {invite_id} by user {created_by}")
            return invite_id
    except Exception as e:
        logger.error(f"Error creating invite by {created_by}: {e}")
        return None


async def use_invite(invite_id: str, user_id: int) -> bool:
    """
    Use an invite link to authorize a user.

    Args:
        invite_id: Invite code
        user_id: Telegram user ID of the user using the invite

    Returns:
        bool: True if invite was used successfully, False otherwise
    """
    try:
        async with get_db_connection() as db:
            # Check if invite exists and is active
            cursor = await db.execute(
                "SELECT id FROM invites WHERE id = ? AND is_active = TRUE AND used_by IS NULL",
                (invite_id,),
            )
            invite = await cursor.fetchone()

            if not invite:
                logger.warning(f"Invalid or used invite: {invite_id}")
                return False

            # Update invite as used
            now = datetime.now().isoformat()
            await db.execute(
                "UPDATE invites SET used_by = ?, used_at = ?, is_active = FALSE WHERE id = ?",
                (user_id, now, invite_id),
            )

            # Add user to authorized users (inline to avoid nested connections)
            cursor = await db.execute("SELECT id FROM users WHERE id = ?", (user_id,))
            existing_user = await cursor.fetchone()

            if existing_user:
                # User exists, update their info
                await db.execute(
                    "UPDATE users SET is_active = TRUE WHERE id = ?",
                    (user_id,),
                )
                logger.info(f"Reactivated existing user via invite: {user_id}")
            else:
                # Add new user
                await db.execute(
                    "INSERT INTO users (id, username, added_by) VALUES (?, ?, ?)",
                    (user_id, None, 0),  # 0 means added via invite
                )
                logger.info(f"Added new user via invite: {user_id}")

            await db.commit()
            logger.info(f"Invite {invite_id} used by user {user_id}")
            return True
    except Exception as e:
        logger.error(f"Error using invite {invite_id} by {user_id}: {e}")
        return False


async def get_all_users() -> List[Dict[str, Any]]:
    """
    Get all users from the database.

    Returns:
        List[Dict]: List of user dictionaries
    """
    try:
        async with get_db_connection() as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("SELECT id, username, added_at, added_by, is_active FROM users")
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]
    except Exception as e:
        logger.error(f"Error getting users: {e}")
        return []


async def deactivate_user(user_id: int) -> bool:
    """
    Deactivate a user.

    Args:
        user_id: Telegram user ID

    Returns:
        bool: True if user was deactivated successfully, False otherwise
    """
    try:
        async with get_db_connection() as db:
            await db.execute("UPDATE users SET is_active = FALSE WHERE id = ?", (user_id,))
            await db.commit()
            logger.info(f"Deactivated user: {user_id}")
            return True
    except Exception as e:
        logger.error(f"Error deactivating user {user_id}: {e}")
        return False
