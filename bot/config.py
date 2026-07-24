"""Configuration module for VideoGrabberBot."""

import os
from pathlib import Path
from typing import Dict

from dotenv import load_dotenv
from loguru import logger

from bot.utils.exceptions import ConfigurationError

# Load environment variables from .env file
load_dotenv()


class Config:
    """Centralized configuration class with validation."""

    def __init__(self) -> None:
        """Initialize configuration with validation."""
        self._validate_and_load()
        self._setup_directories()

    def _validate_and_load(self) -> None:
        """Validate and load all configuration values."""
        # Telegram configuration
        self.TELEGRAM_TOKEN = self._get_required_str("TELEGRAM_TOKEN")
        self.ADMIN_USER_ID = self._get_required_int("ADMIN_USER_ID")

        # Application configuration
        self.BOT_NAME = os.getenv("BOT_NAME", "VideoGrabberBot")
        self.LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()

        # File system paths
        self.BASE_DIR = Path(__file__).parent.parent.absolute()
        self.DATA_DIR = self.BASE_DIR / "data"
        self.TEMP_DIR = self.DATA_DIR / "temp"
        self.DB_PATH = self.DATA_DIR / "bot.db"

        # Download configuration
        self.MAX_FILE_SIZE = int(os.getenv("MAX_FILE_SIZE", str(50 * 1024 * 1024)))  # 50MB Bot API limit
        self.DOWNLOAD_TIMEOUT = int(os.getenv("DOWNLOAD_TIMEOUT", "300"))  # 5 minutes

        # Queue configuration
        self.MAX_QUEUE_SIZE = int(os.getenv("MAX_QUEUE_SIZE", "50"))
        self.MAX_USER_TASKS = int(os.getenv("MAX_USER_TASKS", "5"))

        # Storage configuration
        self.TTL_SECONDS = int(os.getenv("TTL_SECONDS", "3600"))  # 1 hour
        self.MAX_STORAGE_SIZE = int(os.getenv("MAX_STORAGE_SIZE", "1000"))

        # Video and audio formats
        self.VIDEO_FORMATS: Dict[str, Dict[str, str]] = {
            "SD": {"label": "SD (480p)", "format": "best[height<=480]"},
            "HD": {"label": "HD (720p)", "format": "best[height<=720]"},
            "FHD": {"label": "Full HD (1080p)", "format": "best[height<=1080]"},
            "ORIGINAL": {"label": "Original (Max Quality)", "format": "best"},
        }
        self.AUDIO_FORMAT: Dict[str, Dict[str, str]] = {"MP3": {"label": "MP3 (320kbps)", "format": "bestaudio/best"}}

    def _get_required_str(self, key: str) -> str:
        """Get required string environment variable."""
        value = os.getenv(key, "").strip()
        if not value:
            raise ConfigurationError(f"{key} is not set in environment variables", context={"key": key})
        return value

    def _get_required_int(self, key: str) -> int:
        """Get required integer environment variable."""
        value_str = os.getenv(key, "0")
        try:
            value = int(value_str)
            if value <= 0:
                raise ValueError()
            return value
        except ValueError as e:
            raise ConfigurationError(
                f"{key} must be a positive integer, got: {value_str}", context={"key": key, "value": value_str}
            ) from e

    def _setup_directories(self) -> None:
        """Create necessary directories."""
        try:
            self.DATA_DIR.mkdir(exist_ok=True)
            self.TEMP_DIR.mkdir(exist_ok=True)
        except Exception as e:
            raise ConfigurationError(
                f"Failed to create directories: {str(e)}",
                context={"data_dir": str(self.DATA_DIR), "temp_dir": str(self.TEMP_DIR)},
            ) from e

    def validate_all(self) -> None:
        """Perform complete configuration validation."""
        logger.info("Validating configuration...")

        # Validate log level
        valid_levels = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        if self.LOG_LEVEL not in valid_levels:
            raise ConfigurationError(
                f"Invalid LOG_LEVEL: {self.LOG_LEVEL}. Must be one of: {valid_levels}",
                context={"log_level": self.LOG_LEVEL, "valid_levels": list(valid_levels)},
            )

        # Validate numeric ranges
        if self.MAX_FILE_SIZE <= 0:
            raise ConfigurationError("MAX_FILE_SIZE must be positive", context={"value": self.MAX_FILE_SIZE})

        if self.DOWNLOAD_TIMEOUT <= 0:
            raise ConfigurationError("DOWNLOAD_TIMEOUT must be positive", context={"value": self.DOWNLOAD_TIMEOUT})

        logger.info(f"Configuration validated successfully: BOT_NAME={self.BOT_NAME}, LOG_LEVEL={self.LOG_LEVEL}")


# Global configuration instance
config = Config()

# Backward compatibility exports
TELEGRAM_TOKEN = config.TELEGRAM_TOKEN
ADMIN_USER_ID = config.ADMIN_USER_ID
BASE_DIR = config.BASE_DIR
DATA_DIR = config.DATA_DIR
TEMP_DIR = config.TEMP_DIR
DB_PATH = config.DB_PATH
MAX_FILE_SIZE = config.MAX_FILE_SIZE
DOWNLOAD_TIMEOUT = config.DOWNLOAD_TIMEOUT
VIDEO_FORMATS = config.VIDEO_FORMATS
AUDIO_FORMAT = config.AUDIO_FORMAT
