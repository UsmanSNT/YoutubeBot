"""Tests for the configuration module."""

import os

import pytest

from bot.config import Config, ConfigurationError


def test_config_paths():
    """Test that configuration paths are correctly setup."""
    from bot.config import BASE_DIR, DATA_DIR, DB_PATH, TEMP_DIR

    # Check if base directories are set correctly
    assert BASE_DIR.exists()
    assert DATA_DIR.exists()
    assert TEMP_DIR.exists()

    # Verify that DATA_DIR is inside BASE_DIR
    assert str(DATA_DIR).startswith(str(BASE_DIR))

    # Verify that TEMP_DIR is inside DATA_DIR
    assert str(TEMP_DIR).startswith(str(DATA_DIR))

    # Verify DB_PATH is correctly set
    assert DB_PATH.name == "bot.db"
    assert DB_PATH.parent == DATA_DIR


def test_video_formats():
    """Test that video formats are correctly configured."""
    from bot.config import VIDEO_FORMATS

    # Check that we have all the required formats
    assert "SD" in VIDEO_FORMATS
    assert "HD" in VIDEO_FORMATS
    assert "FHD" in VIDEO_FORMATS
    assert "ORIGINAL" in VIDEO_FORMATS

    # Check format structure
    assert "label" in VIDEO_FORMATS["SD"]
    assert "format" in VIDEO_FORMATS["SD"]
    assert "label" in VIDEO_FORMATS["HD"]
    assert "format" in VIDEO_FORMATS["HD"]
    assert "label" in VIDEO_FORMATS["FHD"]
    assert "format" in VIDEO_FORMATS["FHD"]
    assert "label" in VIDEO_FORMATS["ORIGINAL"]
    assert "format" in VIDEO_FORMATS["ORIGINAL"]

    # Check specific format settings
    assert VIDEO_FORMATS["SD"]["format"] == "best[height<=480]"
    assert VIDEO_FORMATS["HD"]["format"] == "best[height<=720]"
    assert VIDEO_FORMATS["FHD"]["format"] == "best[height<=1080]"
    assert VIDEO_FORMATS["ORIGINAL"]["format"] == "best"


def test_audio_format():
    """Test that audio format is correctly configured."""
    from bot.config import AUDIO_FORMAT

    # Check that we have MP3 format
    assert "MP3" in AUDIO_FORMAT

    # Check format structure
    assert "label" in AUDIO_FORMAT["MP3"]
    assert "format" in AUDIO_FORMAT["MP3"]

    # Check specific MP3 format settings
    assert AUDIO_FORMAT["MP3"]["format"] == "bestaudio/best"
    assert AUDIO_FORMAT["MP3"]["label"] == "MP3 (320kbps)"


def test_max_file_size():
    """Test MAX_FILE_SIZE is correctly set."""
    from bot.config import MAX_FILE_SIZE

    # 50MB in bytes (Telegram Bot API file size limit)
    expected_size = 50 * 1024 * 1024
    assert MAX_FILE_SIZE == expected_size


def test_token_validation():
    """Test validation of TELEGRAM_TOKEN."""
    from bot.config import TELEGRAM_TOKEN

    # Token should be set for tests to run
    assert TELEGRAM_TOKEN, "Token should be set for tests to run"
    assert isinstance(TELEGRAM_TOKEN, str)
    assert len(TELEGRAM_TOKEN.strip()) > 0


def test_admin_id_validation():
    """Test validation of ADMIN_USER_ID."""
    from bot.config import ADMIN_USER_ID

    # Admin ID should be set for tests to run
    assert ADMIN_USER_ID, "Admin ID should be set for tests to run"
    assert isinstance(ADMIN_USER_ID, int)
    assert ADMIN_USER_ID > 0


def test_env_variables(mocker):
    """Test environment variables are correctly used."""
    # Mock environment variables
    mocker.patch.dict(os.environ, {"TELEGRAM_TOKEN": "mock_token", "ADMIN_USER_ID": "123456"})

    # We can't easily reload the config module, but we can test
    # that getenv works as expected with our patched environment
    assert os.getenv("TELEGRAM_TOKEN") == "mock_token"
    assert os.getenv("ADMIN_USER_ID") == "123456"

    # And we can test the conversion to int works correctly
    assert int(os.getenv("ADMIN_USER_ID", 0)) == 123456


class TestConfigErrorHandling:
    """Test Config class error handling to improve coverage."""

    def test_get_required_str_empty_value(self, mocker):
        """Test ConfigurationError for empty required string."""
        config = Config()

        mocker.patch.dict(os.environ, {"TEST_KEY": ""})
        with pytest.raises(ConfigurationError, match="TEST_KEY is not set"):
            config._get_required_str("TEST_KEY")

    def test_get_required_str_missing_value(self):
        """Test ConfigurationError for missing required string."""
        config = Config()

        # Ensure key doesn't exist
        if "MISSING_TEST_KEY" in os.environ:
            del os.environ["MISSING_TEST_KEY"]

        with pytest.raises(ConfigurationError, match="MISSING_TEST_KEY is not set"):
            config._get_required_str("MISSING_TEST_KEY")

    def test_get_required_int_invalid_value(self, mocker):
        """Test ConfigurationError for invalid integer value."""
        config = Config()

        mocker.patch.dict(os.environ, {"TEST_INT": "not_a_number"})
        with pytest.raises(ConfigurationError, match="must be a positive integer"):
            config._get_required_int("TEST_INT")

    def test_get_required_int_zero_value(self, mocker):
        """Test ConfigurationError for zero integer value."""
        config = Config()

        mocker.patch.dict(os.environ, {"TEST_INT": "0"})
        with pytest.raises(ConfigurationError, match="must be a positive integer"):
            config._get_required_int("TEST_INT")

    def test_get_required_int_negative_value(self, mocker):
        """Test ConfigurationError for negative integer value."""
        config = Config()

        mocker.patch.dict(os.environ, {"TEST_INT": "-5"})
        with pytest.raises(ConfigurationError, match="must be a positive integer"):
            config._get_required_int("TEST_INT")

    def test_setup_directories_permission_error(self, tmp_path):
        """Test ConfigurationError when directories cannot be created."""
        config = Config()

        # Create a read-only parent directory
        readonly_dir = tmp_path / "readonly"
        readonly_dir.mkdir()
        readonly_dir.chmod(0o444)  # Read-only

        # Try to create subdirectories
        config.DATA_DIR = readonly_dir / "data"
        config.TEMP_DIR = readonly_dir / "temp"

        try:
            with pytest.raises(ConfigurationError, match="Failed to create directories"):
                config._setup_directories()
        finally:
            # Cleanup: restore write permissions
            readonly_dir.chmod(0o755)


class TestConfigValidation:
    """Test Config.validate_all() method to improve coverage."""

    def test_validate_all_success(self, mocker):
        """Test successful validation."""
        _ = Config()

        # Mock valid environment
        mocker.patch.dict(
            os.environ,
            {
                "TELEGRAM_TOKEN": "valid_token",
                "ADMIN_USER_ID": "123456",
                "LOG_LEVEL": "INFO",
                "MAX_FILE_SIZE": "50",
                "DOWNLOAD_TIMEOUT": "300",
            },
        )
        # Create a new config with mocked values
        test_config = Config()
        test_config.LOG_LEVEL = "INFO"
        test_config.MAX_FILE_SIZE = 50
        test_config.DOWNLOAD_TIMEOUT = 300
        test_config.BOT_NAME = "TestBot"

        # Should not raise any exception
        test_config.validate_all()

    def test_validate_all_invalid_log_level(self):
        """Test validation failure for invalid log level."""
        config = Config()
        config.LOG_LEVEL = "INVALID_LEVEL"
        config.MAX_FILE_SIZE = 50
        config.DOWNLOAD_TIMEOUT = 300

        with pytest.raises(ConfigurationError, match="Invalid LOG_LEVEL"):
            config.validate_all()

    def test_validate_all_invalid_max_file_size(self):
        """Test validation failure for invalid max file size."""
        config = Config()
        config.LOG_LEVEL = "INFO"
        config.MAX_FILE_SIZE = -1
        config.DOWNLOAD_TIMEOUT = 300

        with pytest.raises(ConfigurationError, match="MAX_FILE_SIZE must be positive"):
            config.validate_all()

    def test_validate_all_zero_max_file_size(self):
        """Test validation failure for zero max file size."""
        config = Config()
        config.LOG_LEVEL = "INFO"
        config.MAX_FILE_SIZE = 0
        config.DOWNLOAD_TIMEOUT = 300

        with pytest.raises(ConfigurationError, match="MAX_FILE_SIZE must be positive"):
            config.validate_all()

    def test_validate_all_invalid_download_timeout(self):
        """Test validation failure for invalid download timeout."""
        config = Config()
        config.LOG_LEVEL = "INFO"
        config.MAX_FILE_SIZE = 50
        config.DOWNLOAD_TIMEOUT = -1

        with pytest.raises(ConfigurationError, match="DOWNLOAD_TIMEOUT must be positive"):
            config.validate_all()

    def test_validate_all_zero_download_timeout(self):
        """Test validation failure for zero download timeout."""
        config = Config()
        config.LOG_LEVEL = "INFO"
        config.MAX_FILE_SIZE = 50
        config.DOWNLOAD_TIMEOUT = 0

        with pytest.raises(ConfigurationError, match="DOWNLOAD_TIMEOUT must be positive"):
            config.validate_all()

    def test_validate_all_valid_log_levels(self):
        """Test validation succeeds for all valid log levels."""
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]

        for level in valid_levels:
            config = Config()
            config.LOG_LEVEL = level
            config.MAX_FILE_SIZE = 50
            config.DOWNLOAD_TIMEOUT = 300
            config.BOT_NAME = "TestBot"

            # Should not raise any exception
            config.validate_all()
