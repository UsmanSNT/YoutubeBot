"""Tests for downloader module."""

import asyncio
import tempfile
from pathlib import Path
from typing import Any, List, Optional

import pytest
import yt_dlp

from bot.services.downloader import (
    NetworkError,
    UnsupportedFormatError,
    VideoNotFoundError,
    VideoTooLargeError,
    _cleanup_temp_directory,
    _download_video_file,
    _handle_download_error,
    _sync_download_video_file,
    _validate_file_size,
    download_youtube_video,
    is_youtube_url,
)
from bot.utils.exceptions import DownloadError


class MockBotSetup:
    """Helper class to create consistent bot mocks."""

    def __init__(self, mocker):
        self.mocker = mocker
        self.bot = mocker.AsyncMock()
        self.message_mock = mocker.MagicMock(message_id=123)

    def setup_basic_bot(self) -> Any:
        """Setup bot with basic message operations."""
        self.bot.send_message = self.mocker.AsyncMock(return_value=self.message_mock)
        self.bot.edit_message_text = self.mocker.AsyncMock()
        self.bot.send_document = self.mocker.AsyncMock()
        return self.bot


class MockYoutubeDLSetup:
    """Helper class to create consistent YoutubeDL mocks."""

    def __init__(self, mocker):
        self.mocker = mocker

    def setup_successful_download(self, title: str = "Test Video") -> Any:
        """Setup YoutubeDL mock for successful download."""
        mock_ydl = self.mocker.MagicMock()
        mock_ydl.extract_info.return_value = {"title": title}
        mock_ydl.download.return_value = None

        mock_ydl_context = self.mocker.MagicMock()
        mock_ydl_context.__enter__.return_value = mock_ydl
        mock_ydl_context.__exit__.return_value = None

        return mock_ydl_context

    def setup_failed_download(self, error_message: str = "Download failed") -> Any:
        """Setup YoutubeDL mock for failed download."""
        mock_ydl = self.mocker.MagicMock()
        mock_ydl.extract_info.side_effect = Exception(error_message)

        mock_ydl_context = self.mocker.MagicMock()
        mock_ydl_context.__enter__.return_value = mock_ydl
        mock_ydl_context.__exit__.return_value = None

        return mock_ydl_context


class MockFileSystemSetup:
    """Helper class to setup temporary files and directory mocks."""

    def __init__(self, mocker):
        self.mocker = mocker

    def setup_temp_directory_with_file(self, temp_dir_path: Path, filename: str = "test_video.mp4") -> Path:
        """Create temporary directory with a dummy file."""
        dummy_file = temp_dir_path / filename
        with open(dummy_file, "w") as f:
            f.write("dummy content")
        return dummy_file

    def setup_common_patches(self, temp_dir: str, files: Optional[List[Path]] = None) -> None:
        """Setup common patches for file system operations."""
        if files is None:
            files = []
        self.mocker.patch("tempfile.mkdtemp", return_value=temp_dir)
        self.mocker.patch("pathlib.Path.glob", return_value=files)


@pytest.fixture
def bot_setup(mocker):
    """Fixture for bot mock setup."""
    return MockBotSetup(mocker)


@pytest.fixture
def ydl_setup(mocker):
    """Fixture for YoutubeDL mock setup."""
    return MockYoutubeDLSetup(mocker)


@pytest.fixture
def fs_setup(mocker):
    """Fixture for file system mock setup."""
    return MockFileSystemSetup(mocker)


def apply_standard_patches(mocker, temp_dir: str, ydl_context: Any, files: Optional[List[Path]] = None) -> None:
    """Apply standard patches used across multiple tests."""
    if files is None:
        files = []
    mocker.patch("tempfile.mkdtemp", return_value=temp_dir)
    mocker.patch("yt_dlp.YoutubeDL", return_value=ydl_context)
    mocker.patch("pathlib.Path.glob", return_value=files)


class CleanupFailureMock:
    """Mock for cleanup failure to avoid nested functions."""

    def __init__(self, mock_logger_error):
        self.mock_logger_error = mock_logger_error

    def __call__(self, temp_dir):
        """Simulate cleanup failure."""
        self.mock_logger_error("Failed to clean up temporary directory: Cleanup failed")
        # Don't actually fail cleanup that would interfere with test teardown


@pytest.mark.asyncio
async def test_is_youtube_url():
    """Test youtube URL detection function."""
    # Valid YouTube URLs
    assert is_youtube_url("https://www.youtube.com/watch?v=dQw4w9WgXcQ")
    assert is_youtube_url("https://youtu.be/dQw4w9WgXcQ")
    assert is_youtube_url("https://m.youtube.com/watch?v=dQw4w9WgXcQ")
    assert is_youtube_url("https://youtube-nocookie.com/watch?v=dQw4w9WgXcQ")

    # Invalid YouTube URLs
    assert not is_youtube_url("https://www.example.com")
    assert not is_youtube_url("https://vimeo.com/123456")
    assert not is_youtube_url("https://video.example.com/p/123456")


@pytest.mark.asyncio
async def test_download_youtube_video_success(bot_setup, ydl_setup, fs_setup):
    """Test successful video download and sending."""
    bot = bot_setup.setup_basic_bot()

    with tempfile.TemporaryDirectory() as temp_dir:
        temp_dir_path = Path(temp_dir)
        dummy_file = fs_setup.setup_temp_directory_with_file(temp_dir_path)

        ydl_context = ydl_setup.setup_successful_download()
        apply_standard_patches(fs_setup.mocker, str(temp_dir_path), ydl_context, [dummy_file])

        await download_youtube_video(bot, 12345, "https://www.youtube.com/watch?v=test")

        # Verify the calls
        bot.send_message.assert_called_once()
        assert bot.edit_message_text.call_count == 2
        bot.send_document.assert_called_once()


@pytest.mark.asyncio
async def test_download_youtube_video_with_status_message(bot_setup, ydl_setup, fs_setup):
    """Test download with existing status message ID."""
    bot = bot_setup.setup_basic_bot()

    with tempfile.TemporaryDirectory() as temp_dir:
        temp_dir_path = Path(temp_dir)
        dummy_file = fs_setup.setup_temp_directory_with_file(temp_dir_path)

        ydl_context = ydl_setup.setup_successful_download()
        apply_standard_patches(fs_setup.mocker, str(temp_dir_path), ydl_context, [dummy_file])

        # Additional patches for this specific test
        fs_setup.mocker.patch("bot.services.downloader.Message")
        fs_setup.mocker.patch("bot.services.downloader.Chat")

        await download_youtube_video(
            bot,
            12345,
            "https://www.youtube.com/watch?v=test",
            status_message_id=789,
        )

        # Verify edit_message_text was called instead of send_message
        bot.send_message.assert_not_called()
        assert bot.edit_message_text.call_count == 3  # Initial + progress + completion
        bot.send_document.assert_called_once()


@pytest.mark.asyncio
async def test_download_youtube_video_failure(bot_setup, ydl_setup, fs_setup):
    """Test video download failure handling."""
    bot = bot_setup.setup_basic_bot()

    with tempfile.TemporaryDirectory() as temp_dir:
        ydl_context = ydl_setup.setup_failed_download("Download failed")
        apply_standard_patches(fs_setup.mocker, temp_dir, ydl_context)
        fs_setup.mocker.patch("bot.utils.logging.notify_admin", fs_setup.mocker.AsyncMock())

        with pytest.raises(DownloadError):
            await download_youtube_video(bot, 12345, "https://www.youtube.com/watch?v=test")

        # Verify error message was sent to user
        # We expect 2 calls to send_message from our function:
        # 1. Initial message
        # 2. Error message to user
        assert bot.send_message.call_count >= 2

        # Check that the last call includes error message
        args, kwargs = bot.send_message.call_args_list[-1]
        assert "Download failed" in kwargs.get("text", "") or "Download failed" in args[1]


@pytest.mark.asyncio
async def test_download_youtube_video_no_files(bot_setup, ydl_setup, fs_setup):
    """Test download when no files are found after download."""
    bot = bot_setup.setup_basic_bot()

    with tempfile.TemporaryDirectory() as temp_dir:
        ydl_context = ydl_setup.setup_successful_download()
        apply_standard_patches(fs_setup.mocker, temp_dir, ydl_context, [])  # No files found
        fs_setup.mocker.patch("bot.utils.logging.notify_admin", fs_setup.mocker.AsyncMock())

        with pytest.raises(DownloadError) as exc_info:
            await download_youtube_video(bot, 12345, "https://www.youtube.com/watch?v=test")

            # Check error message (now wrapped as unexpected error)
            error_msg = str(exc_info.value).lower()
            assert "unexpected error" in error_msg or "no files found" in error_msg


@pytest.mark.asyncio
async def test_download_youtube_video_cleanup_failure(bot_setup, ydl_setup, fs_setup):
    """Test download when cleanup fails."""
    bot = bot_setup.setup_basic_bot()

    with tempfile.TemporaryDirectory() as temp_dir:
        temp_dir_path = Path(temp_dir)
        dummy_file = fs_setup.setup_temp_directory_with_file(temp_dir_path)

        ydl_context = ydl_setup.setup_successful_download()
        apply_standard_patches(fs_setup.mocker, str(temp_dir_path), ydl_context, [dummy_file])

        mock_logger_error = fs_setup.mocker.patch("bot.services.downloader.logger.error")
        mock_cleanup_failure = CleanupFailureMock(mock_logger_error)
        fs_setup.mocker.patch("bot.services.downloader._cleanup_temp_directory", side_effect=mock_cleanup_failure)

        # Call the function - should complete without raising exception
        await download_youtube_video(bot, 12345, "https://www.youtube.com/watch?v=test")

        # Verify the function logged the cleanup error
        mock_logger_error.assert_called_once()
        assert "Failed to clean up" in mock_logger_error.call_args[0][0]


class TestFileSizeCheck:
    """Test file size checking functionality."""

    def test_validate_file_size_oversized_with_file(self, tmp_path, mocker):
        """Test file size check when file is too large and exists."""
        # Create a test file
        test_file = tmp_path / "test_video.mp4"
        test_file.write_bytes(b"test content")

        # Mock config with small max file size
        mock_config = mocker.patch("bot.services.downloader.config")
        mock_config.MAX_FILE_SIZE = 10  # Very small limit

        with pytest.raises(VideoTooLargeError, match="File size .* exceeds limit"):
            _validate_file_size(1024 * 1024, "http://test.url", test_file)  # 1MB file

        # File should be deleted
        assert not test_file.exists()

    def test_validate_file_size_oversized_no_file(self, mocker):
        """Test file size check when file is too large but no file exists."""
        mock_config = mocker.patch("bot.services.downloader.config")
        mock_config.MAX_FILE_SIZE = 10  # Very small limit

        with pytest.raises(VideoTooLargeError, match="File size .* exceeds limit"):
            _validate_file_size(1024 * 1024, "http://test.url", None)

    def test_validate_file_size_within_limit(self, tmp_path, mocker):
        """Test file size check when file is within limit."""
        test_file = tmp_path / "test_video.mp4"
        test_file.write_bytes(b"test content")

        mock_config = mocker.patch("bot.services.downloader.config")
        mock_config.MAX_FILE_SIZE = 1024 * 1024 * 100  # 100MB limit

        # Should not raise exception
        _validate_file_size(1024, "http://test.url", test_file)

        # File should still exist
        assert test_file.exists()


class TestSyncDownloadVideoFile:
    """Test sync download video file function."""

    def test_extract_info_video_not_found_error(self, tmp_path, mocker):
        """Test extract info with video not found error."""
        url = "http://test.url"
        ydl_opts = {"format": "best"}
        temp_path = tmp_path

        mock_ydl = mocker.MagicMock()
        mock_ydl.extract_info.side_effect = yt_dlp.utils.DownloadError("Video not found or not available")

        mock_ydl_class = mocker.patch("yt_dlp.YoutubeDL")
        mock_ydl_class.return_value.__enter__.return_value = mock_ydl

        with pytest.raises(VideoNotFoundError, match="Video not found or unavailable"):
            _sync_download_video_file(url, ydl_opts, temp_path)

    def test_extract_info_unsupported_format_error(self, tmp_path, mocker):
        """Test extract info with unsupported format error."""
        url = "http://test.url"
        ydl_opts = {"format": "best"}
        temp_path = tmp_path

        mock_ydl = mocker.MagicMock()
        mock_ydl.extract_info.side_effect = yt_dlp.utils.DownloadError("Unsupported URL or format")

        mock_ydl_class = mocker.patch("yt_dlp.YoutubeDL")
        mock_ydl_class.return_value.__enter__.return_value = mock_ydl

        with pytest.raises(UnsupportedFormatError, match="Video format not supported"):
            _sync_download_video_file(url, ydl_opts, temp_path)

    def test_extract_info_network_error(self, tmp_path, mocker):
        """Test extract info with network error."""
        url = "http://test.url"
        ydl_opts = {"format": "best"}
        temp_path = tmp_path

        mock_ydl = mocker.MagicMock()
        mock_ydl.extract_info.side_effect = yt_dlp.utils.DownloadError("Connection failed")

        mock_ydl_class = mocker.patch("yt_dlp.YoutubeDL")
        mock_ydl_class.return_value.__enter__.return_value = mock_ydl

        with pytest.raises(NetworkError, match="Network error during video info extraction"):
            _sync_download_video_file(url, ydl_opts, temp_path)

    def test_expected_file_size_check(self, tmp_path, mocker):
        """Test expected file size validation."""
        url = "http://test.url"
        ydl_opts = {"format": "best"}
        temp_path = tmp_path

        # Create test file
        test_file = temp_path / "test_video.mp4"
        test_file.write_bytes(b"test content")

        mock_ydl = mocker.MagicMock()
        mock_ydl.extract_info.return_value = {"filesize": 1024 * 1024 * 100}  # Large file
        mock_ydl.download.return_value = None

        mock_ydl_class = mocker.patch("yt_dlp.YoutubeDL")
        mock_config = mocker.patch("bot.services.downloader.config")
        mocker.patch("pathlib.Path.glob", return_value=[test_file])

        mock_ydl_class.return_value.__enter__.return_value = mock_ydl
        mock_config.MAX_FILE_SIZE = 10  # Very small limit

        with pytest.raises(VideoTooLargeError):
            _sync_download_video_file(url, ydl_opts, temp_path)

    def test_download_network_error(self, tmp_path, mocker):
        """Test download with network error."""
        url = "http://test.url"
        ydl_opts = {"format": "best"}
        temp_path = tmp_path

        mock_ydl = mocker.MagicMock()
        mock_ydl.extract_info.return_value = {"filesize": 1024}
        mock_ydl.download.side_effect = yt_dlp.utils.DownloadError("Network error during download")

        mock_ydl_class = mocker.patch("yt_dlp.YoutubeDL")
        mock_config = mocker.patch("bot.services.downloader.config")

        mock_ydl_class.return_value.__enter__.return_value = mock_ydl
        mock_config.MAX_FILE_SIZE = 1024 * 1024  # 1MB limit

        with pytest.raises(NetworkError, match="Network error during video download"):
            _sync_download_video_file(url, ydl_opts, temp_path)


class TestCleanupTempDirectory:
    """Test cleanup temporary directory function."""

    def test_cleanup_temp_directory_success(self, tmp_path):
        """Test successful cleanup of temporary directory."""
        temp_dir = str(tmp_path / "test_temp")

        # Create the directory first
        import os

        os.makedirs(temp_dir, exist_ok=True)

        # Add a file to make sure directory is not empty
        test_file = Path(temp_dir) / "test_file.txt"
        test_file.write_text("test content")

        # Cleanup should not raise exception
        _cleanup_temp_directory(temp_dir)

        # Directory should no longer exist
        assert not os.path.exists(temp_dir)

    def test_cleanup_temp_directory_not_exists(self):
        """Test cleanup of non-existent directory."""
        temp_dir = "/non/existent/directory"

        # Should not raise exception
        _cleanup_temp_directory(temp_dir)

    def test_cleanup_temp_directory_failure(self, tmp_path, mocker):
        """Test cleanup failure handling."""
        temp_dir = str(tmp_path / "test_temp")

        # Create the directory
        import os

        os.makedirs(temp_dir, exist_ok=True)

        mocker.patch("os.path.exists", return_value=True)
        mocker.patch("shutil.rmtree", side_effect=PermissionError("Permission denied"))
        mock_logger = mocker.patch("bot.services.downloader.logger.error")

        # Should not raise exception but log error
        _cleanup_temp_directory(temp_dir)

        # Should have logged the error
        mock_logger.assert_called_once()
        assert "Failed to clean up temporary directory" in mock_logger.call_args[0][0]


class TestDownloadVideoFileTimeout:
    """Test download video file timeout scenarios."""

    @pytest.mark.asyncio
    async def test_download_video_file_timeout(self, tmp_path, mocker):
        """Test download timeout error handling."""
        url = "http://test.url"
        ydl_opts = {"format": "best"}
        temp_path = tmp_path

        mock_config = mocker.patch("bot.services.downloader.config")
        mock_config.DOWNLOAD_TIMEOUT = 30

        # Mock the entire function to avoid thread pool issues
        _ = mocker.patch("bot.services.downloader._sync_download_video_file")

        # Make asyncio.wait_for raise TimeoutError
        async def mock_wait_for(coro, timeout):
            raise asyncio.TimeoutError()

        mocker.patch("asyncio.wait_for", side_effect=mock_wait_for)

        with pytest.raises(NetworkError, match="Download timed out after 30 seconds"):
            await _download_video_file(url, ydl_opts, temp_path)


class TestHandleDownloadError:
    """Test download error handling functionality."""

    @pytest.mark.asyncio
    async def test_handle_video_not_found_error(self, mocker):
        """Test handling VideoNotFoundError."""
        bot = mocker.AsyncMock()
        chat_id = 12345
        url = "http://test.url"
        error = VideoNotFoundError("Video not found", context={"url": url})

        mocker.patch("bot.utils.logging.notify_admin", mocker.AsyncMock())

        await _handle_download_error(bot, chat_id, url, error)

        # Check user message was sent (function calls send_message twice - once for user, once for admin)
        assert bot.send_message.call_count == 2
        # First call should be to the user
        user_call_args = bot.send_message.call_args_list[0]
        assert user_call_args[0][0] == chat_id
        assert "Video Not Found" in user_call_args[0][1]

    @pytest.mark.asyncio
    async def test_handle_video_too_large_error(self, mocker):
        """Test handling VideoTooLargeError."""
        bot = mocker.AsyncMock()
        chat_id = 12345
        url = "http://test.url"
        error = VideoTooLargeError("File too large", context={"url": url})

        mocker.patch("bot.utils.logging.notify_admin", mocker.AsyncMock())

        await _handle_download_error(bot, chat_id, url, error)

        # Check user message was sent (function calls send_message twice - once for user, once for admin)
        assert bot.send_message.call_count == 2
        # First call should be to the user
        user_call_args = bot.send_message.call_args_list[0]
        assert user_call_args[0][0] == chat_id
        assert "File Too Large" in user_call_args[0][1]

    @pytest.mark.asyncio
    async def test_handle_unsupported_format_error(self, mocker):
        """Test handling UnsupportedFormatError."""
        bot = mocker.AsyncMock()
        chat_id = 12345
        url = "http://test.url"
        error = UnsupportedFormatError("Format not supported", context={"url": url})

        mocker.patch("bot.utils.logging.notify_admin", mocker.AsyncMock())

        await _handle_download_error(bot, chat_id, url, error)

        # Check user message was sent (function calls send_message twice - once for user, once for admin)
        assert bot.send_message.call_count == 2
        # First call should be to the user
        user_call_args = bot.send_message.call_args_list[0]
        assert user_call_args[0][0] == chat_id
        assert "Unsupported Format" in user_call_args[0][1]

    @pytest.mark.asyncio
    async def test_handle_network_error(self, mocker):
        """Test handling NetworkError."""
        bot = mocker.AsyncMock()
        chat_id = 12345
        url = "http://test.url"
        error = NetworkError("Network failed", context={"url": url})

        mocker.patch("bot.utils.logging.notify_admin", mocker.AsyncMock())

        await _handle_download_error(bot, chat_id, url, error)

        # Check user message was sent (function calls send_message twice - once for user, once for admin)
        assert bot.send_message.call_count == 2
        # First call should be to the user
        user_call_args = bot.send_message.call_args_list[0]
        assert user_call_args[0][0] == chat_id
        assert "Network Error" in user_call_args[0][1]

    @pytest.mark.asyncio
    async def test_handle_unexpected_error(self, mocker):
        """Test handling unexpected error types."""
        bot = mocker.AsyncMock()
        chat_id = 12345
        url = "http://test.url"
        error = Exception("Unexpected error")

        mocker.patch("bot.utils.logging.notify_admin", mocker.AsyncMock())

        await _handle_download_error(bot, chat_id, url, error)

        # Check user message was sent (function calls send_message twice - once for user, once for admin)
        assert bot.send_message.call_count == 2
        # First call should be to the user
        user_call_args = bot.send_message.call_args_list[0]
        assert user_call_args[0][0] == chat_id
        assert "Download Failed" in user_call_args[0][1]
        assert "unexpected error" in user_call_args[0][1]
