# bot/services/storage.py
"""Temporary storage for handling URL data."""

import time
import uuid
from typing import Dict, Optional, Tuple

from bot.config import config

# URL_STORAGE format: {url_id: (url, format_id, timestamp)}
URL_STORAGE: Dict[str, Tuple[str, Optional[str], float]] = {}


def _cleanup_expired_entries() -> None:
    """Remove expired entries from storage."""
    current_time = time.time()
    expired_keys = [
        key for key, (_, _, timestamp) in URL_STORAGE.items() if current_time - timestamp > config.TTL_SECONDS
    ]
    for key in expired_keys:
        URL_STORAGE.pop(key, None)


def _enforce_size_limit() -> None:
    """Enforce maximum storage size by removing oldest entries."""
    if len(URL_STORAGE) <= config.MAX_STORAGE_SIZE:
        return

    # Sort by timestamp and keep only the newest entries
    sorted_items = sorted(URL_STORAGE.items(), key=lambda x: x[1][2], reverse=True)
    URL_STORAGE.clear()
    for key, item_value in sorted_items[: config.MAX_STORAGE_SIZE]:
        URL_STORAGE[key] = item_value


def _get_storage_data(url_id: str, index: int) -> Optional[str]:
    """Get data from storage by URL ID and tuple index.

    Args:
        url_id: URL ID
        index: Index in storage tuple (0=url, 1=format_id)

    Returns:
        Data at specified index or None if not found
    """
    _cleanup_expired_entries()
    storage_data = URL_STORAGE.get(url_id)
    if storage_data:
        value = storage_data[index]
        return value if isinstance(value, str) else None
    return None


def store_url(url: str) -> str:
    """
    Store URL in temporary storage and return unique ID.

    Args:
        url: URL to store

    Returns:
        Unique ID for the URL
    """
    _cleanup_expired_entries()
    _enforce_size_limit()

    url_id = str(uuid.uuid4())[:8]  # Short UUID
    URL_STORAGE[url_id] = (url, None, time.time())
    return url_id


def get_url(url_id: str) -> Optional[str]:
    """
    Get URL by ID.

    Args:
        url_id: URL ID

    Returns:
        URL or None if not found
    """
    return _get_storage_data(url_id, 0)


def store_format(url_id: str, format_id: str) -> bool:
    """
    Store format ID for URL.

    Args:
        url_id: URL ID
        format_id: Format ID

    Returns:
        True if success, False if URL not found
    """
    _cleanup_expired_entries()
    existing_data = URL_STORAGE.get(url_id)
    if existing_data is None:
        return False

    url, _, timestamp = existing_data
    URL_STORAGE[url_id] = (url, format_id, timestamp)
    return True


def get_format(url_id: str) -> Optional[str]:
    """
    Get format ID for URL.

    Args:
        url_id: URL ID

    Returns:
        Format ID or None if not found
    """
    return _get_storage_data(url_id, 1)


def clear_url(url_id: str) -> None:
    """
    Remove URL from storage.

    Args:
        url_id: URL ID
    """
    URL_STORAGE.pop(url_id, None)
