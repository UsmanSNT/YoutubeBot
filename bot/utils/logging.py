"""Logging configuration module for VideoGrabberBot."""

import sys
from pathlib import Path
from typing import Any, Dict, Optional, Union

from aiogram import Bot
from loguru import logger

from bot.config import ADMIN_USER_ID, DATA_DIR


def _log_admin_message(level: str, message: str, kwargs: Dict[str, Any]) -> None:
    """Log admin notification message."""
    if level == "ERROR":
        logger.error(f"Admin notification: {message}", **kwargs)
    else:
        logger.log(level, f"Admin notification: {message}", **kwargs)


def _format_admin_message(level: str, message: str, kwargs: Dict[str, Any]) -> str:
    """Format message for Telegram admin notification."""
    parts = [f"⚠️ {level} ⚠️", "", message]

    if kwargs:
        parts.extend(["", "Additional data:"])
        parts.extend(f"- {key}: {data_value}" for key, data_value in kwargs.items())

    return "\n".join(parts)


def setup_logger(log_file: Optional[Union[str, Path]] = None) -> None:
    """
    Configure Loguru logger.

    Args:
        log_file: Path to the log file. If None, logs will be saved to DATA_DIR/bot.log
    """
    # Remove default handler
    logger.remove()

    # Set default log file if not provided
    if log_file is None:
        log_file = DATA_DIR / "bot.log"

    # Configure logger format
    log_format = (
        "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
        "<level>{level: <8}</level> | "
        "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
        "<level>{message}</level>"
    )

    # Add console handler (INFO level and above)
    logger.add(
        sys.stdout,
        format=log_format,
        level="INFO",
        colorize=True,
    )

    # Add file handler (DEBUG level and above)
    logger.add(
        log_file,
        format=log_format,
        level="DEBUG",
        rotation="10 MB",
        compression="zip",
        retention="1 month",
    )

    logger.info(f"Logger initialized. Log file: {log_file}")


async def notify_admin(bot: Bot, message: str, level: str = "ERROR", **kwargs: Any) -> None:
    """
    Send notification message to admin.

    Args:
        bot: Initialized Bot instance
        message: Message text to send
        level: Log level (e.g., 'ERROR', 'INFO')
        **kwargs: Additional data to include in the log
    """
    try:
        _log_admin_message(level, message, kwargs)
    except Exception as e:
        logger.error(f"Failed to log admin message: {e}")
        return

    try:
        formatted_message = _format_admin_message(level, message, kwargs)
    except Exception as e:
        logger.error(f"Failed to format admin message: {e}")
        return

    try:
        await bot.send_message(ADMIN_USER_ID, formatted_message)
    except Exception as e:
        logger.error(f"Failed to notify admin: {e}")
