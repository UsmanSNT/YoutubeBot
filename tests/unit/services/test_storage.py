"""Tests for the storage module."""

import time

from bot.config import config
from bot.services.storage import (
    URL_STORAGE,
    clear_url,
    get_format,
    get_url,
    store_format,
    store_url,
)


class TestStorageBasics:
    """Test basic storage functionality."""

    def test_url_storage_lifecycle(self):
        """Test full lifecycle of URL storage: store, get, update, clear."""
        # Store a URL and verify it returns a valid ID
        url = "https://www.youtube.com/watch?v=test123"
        url_id = store_url(url)

        # Verify ID properties
        assert isinstance(url_id, str)
        assert len(url_id) == 8  # Should be a short UUID

        # Retrieve URL and verify it matches
        retrieved_url = get_url(url_id)
        assert retrieved_url == url

        # Verify format is initially None
        assert get_format(url_id) is None

        # Store format and verify success
        format_id = "video:TEST_HD"
        format_stored = store_format(url_id, format_id)
        assert format_stored is True

        # Retrieve format and verify
        retrieved_format = get_format(url_id)
        assert retrieved_format == format_id

        # Clear URL and verify it's gone
        clear_url(url_id)
        assert get_url(url_id) is None
        assert get_format(url_id) is None

    def test_multiple_urls(self):
        """Test handling multiple URLs simultaneously."""
        # Store multiple URLs
        url1 = "https://www.youtube.com/watch?v=test1"
        url2 = "https://www.youtube.com/watch?v=test2"

        url_id1 = store_url(url1)
        url_id2 = store_url(url2)

        # Verify they're different IDs
        assert url_id1 != url_id2

        # Verify correct URLs are retrieved
        assert get_url(url_id1) == url1
        assert get_url(url_id2) == url2

        # Store formats
        store_format(url_id1, "video:TEST_SD")
        store_format(url_id2, "audio:TEST_MP3")

        # Verify formats
        assert get_format(url_id1) == "video:TEST_SD"
        assert get_format(url_id2) == "audio:TEST_MP3"

        # Clear one URL
        clear_url(url_id1)

        # Verify first URL is gone but second remains
        assert get_url(url_id1) is None
        assert get_format(url_id1) is None
        assert get_url(url_id2) == url2
        assert get_format(url_id2) == "audio:TEST_MP3"

        # Clean up second URL
        clear_url(url_id2)

    def test_nonexistent_url(self):
        """Test operations on nonexistent URLs."""
        # Generate a random ID that shouldn't exist
        nonexistent_id = "nonexist"

        # Try to get a nonexistent URL
        assert get_url(nonexistent_id) is None
        assert get_format(nonexistent_id) is None

        # Try to store a format for nonexistent URL
        format_stored = store_format(nonexistent_id, "video:TEST_HD")
        assert format_stored is False

        # Clear nonexistent URL should not raise errors
        clear_url(nonexistent_id)  # Should not raise

    def test_invalid_inputs(self):
        """Test handling of invalid inputs."""
        # Empty URL
        url_id = store_url("")
        assert isinstance(url_id, str)
        assert get_url(url_id) == ""
        clear_url(url_id)

        # Empty format ID
        url_id = store_url("https://example.com")
        assert store_format(url_id, "") is True
        assert get_format(url_id) == ""
        clear_url(url_id)

        # For invalid URL IDs (not testing None - handled by type checking)
        assert get_url("non_existent_id") is None
        assert store_format("non_existent_id", "some_format") is False
        assert get_format("non_existent_id") is None

    def test_update_url_format(self):
        """Test updating format for the same URL."""
        url = "https://www.youtube.com/watch?v=updatetest"
        url_id = store_url(url)

        # Set initial format
        initial_format = "video:SD"
        assert store_format(url_id, initial_format) is True
        assert get_format(url_id) == initial_format

        # Update format
        new_format = "video:HD"
        assert store_format(url_id, new_format) is True
        assert get_format(url_id) == new_format

        # Get the storage data directly and verify (format: url, format_id, timestamp)
        storage_data = URL_STORAGE.get(url_id)
        assert storage_data[0] == url
        assert storage_data[1] == new_format
        assert isinstance(storage_data[2], float)  # timestamp


class TestStorageAdvanced:
    """Test advanced storage scenarios."""

    def test_uuid_collision_handling(self, mocker):
        """Test handling of UUID collisions."""
        # Mock uuid to always return the same value
        test_uuid = "12345678"
        mocker.patch("uuid.uuid4", return_value=test_uuid)

        # First store should succeed
        url1 = "https://example.com/test1"
        url_id1 = store_url(url1)
        assert url_id1 == test_uuid[:8]
        assert get_url(url_id1) == url1

        # Second store with same uuid should generate a different ID
        # In real implementation, this would need collision handling
        url2 = "https://example.com/test2"
        url_id2 = store_url(url2)
        assert url_id2 == test_uuid[:8]  # Since we're mocking uuid
        assert get_url(url_id2) == url2  # Latest value overwrites

    def test_storage_direct_access(self):
        """Test direct access to URL_STORAGE (for internal code)."""
        url = "https://test.example.com"
        url_id = store_url(url)

        # Verify internal structure (format: url, format_id, timestamp)
        assert url_id in URL_STORAGE
        storage_data = URL_STORAGE[url_id]
        assert storage_data[0] == url
        assert storage_data[1] is None
        assert isinstance(storage_data[2], float)  # timestamp

        # Store format and verify internal structure
        format_id = "video:HD"
        store_format(url_id, format_id)
        storage_data = URL_STORAGE[url_id]
        assert storage_data[0] == url
        assert storage_data[1] == format_id
        assert isinstance(storage_data[2], float)  # timestamp

    def test_storage_isolation(self):
        """Test that storage is properly isolated between tests."""
        # This test validates that the reset_storage fixture works
        # First, make sure storage is empty (default fixture behavior)
        current_size = len(URL_STORAGE)

        # Add an item
        url_id = store_url("https://isolation-test.com")

        # Verify it exists
        assert len(URL_STORAGE) == current_size + 1
        assert url_id in URL_STORAGE

        # The reset_storage fixture (autouse) will clean up after the test

    def test_many_urls(self):
        """Test with a large number of URLs."""
        # Store a larger number of URLs
        url_base = "https://example.com/video/"
        url_ids = []

        for i in range(50):
            url = f"{url_base}{i}"
            url_id = store_url(url)
            url_ids.append(url_id)

        # Verify all URLs were stored correctly
        assert len(url_ids) == 50

        # Verify all can be retrieved correctly
        for i, url_id in enumerate(url_ids):
            expected_url = f"{url_base}{i}"
            assert get_url(url_id) == expected_url

        # Store formats for all
        for i, url_id in enumerate(url_ids):
            format_type = "video" if i % 2 == 0 else "audio"
            format_id = f"{format_type}:FORMAT_{i}"
            assert store_format(url_id, format_id) is True
            assert get_format(url_id) == format_id

        # Clear half of them
        for i, url_id in enumerate(url_ids):
            if i % 2 == 0:
                clear_url(url_id)

        # Count remaining items
        remaining_count = 0
        for url_id in url_ids:
            if get_url(url_id) is not None:
                remaining_count += 1

        # Verify half are gone and half remain
        assert remaining_count == 25

        for i, url_id in enumerate(url_ids):
            if i % 2 == 0:
                assert get_url(url_id) is None
                assert get_format(url_id) is None
            else:
                assert get_url(url_id) == f"{url_base}{i}"
                assert get_format(url_id) == f"audio:FORMAT_{i}"


class TestStorageInternals:
    """Test internal storage mechanics: expiry and size limits."""

    def test_cleanup_expired_entries(self):
        """Test that expired entries are removed during storage operations."""
        old_url_id = "old12345"
        old_timestamp = time.time() - (config.TTL_SECONDS + 100)
        URL_STORAGE[old_url_id] = ("https://expired.com", None, old_timestamp)

        assert old_url_id in URL_STORAGE

        new_url_id = store_url("https://fresh.com")

        assert old_url_id not in URL_STORAGE
        assert get_url(old_url_id) is None
        assert get_url(new_url_id) == "https://fresh.com"

    def test_enforce_size_limit(self, mocker):
        """Test that storage size limit evicts oldest entries."""
        from bot.services import storage as storage_module

        mocker.patch.object(storage_module.config, "MAX_STORAGE_SIZE", 2)

        # Use a counter so time.time() never exhausts (each call returns increasing value)
        _counter = [0.0]

        def _make_time() -> float:
            _counter[0] += 1.0
            return _counter[0]

        mocker.patch("bot.services.storage.time.time", side_effect=_make_time)

        url_id1 = store_url("https://example.com/1")
        url_id2 = store_url("https://example.com/2")
        url_id3 = store_url("https://example.com/3")

        # Adding 4th item triggers _enforce_size_limit (len=3 > MAX=2)
        url_id4 = store_url("https://example.com/4")

        assert get_url(url_id1) is None
        assert get_url(url_id2) == "https://example.com/2"
        assert get_url(url_id3) == "https://example.com/3"
        assert get_url(url_id4) == "https://example.com/4"
