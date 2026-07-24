# bot/utils/exceptions.py
"""Custom exceptions for VideoGrabberBot."""

from typing import Any, Dict, Optional


class VideoGrabberBotError(Exception):
    """Base exception for VideoGrabberBot."""

    def __init__(self, message: str, context: Optional[Dict[str, Any]] = None) -> None:
        """Initialize exception with message and optional context."""
        super().__init__(message)
        self.context = context or {}


class DownloadError(VideoGrabberBotError):
    """Base exception for download-related errors."""


class NetworkError(DownloadError):
    """Network-related download errors."""


class VideoNotFoundError(DownloadError):
    """Video not found or unavailable errors."""


class VideoTooLargeError(DownloadError):
    """Video file size exceeds limits."""


class UnsupportedFormatError(DownloadError):
    """Requested video format is not supported."""


class AuthenticationError(VideoGrabberBotError):
    """User authentication errors."""


class QueueError(VideoGrabberBotError):
    """Queue management errors."""


class QueueFullError(QueueError):
    """Queue capacity exceeded."""


class StorageError(VideoGrabberBotError):
    """Storage-related errors."""


class ConfigurationError(VideoGrabberBotError):
    """Configuration-related errors."""


class RateLimitError(VideoGrabberBotError):
    """Rate limiting errors."""
