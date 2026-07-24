"""Download handler for processing video links."""

from typing import List, Optional, Tuple

from aiogram import F, Router  # noqa: WPS347
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)
from loguru import logger

from bot.services.downloader import is_youtube_url
from bot.services.formats import FormatData, get_format_by_id, get_format_options
from bot.services.queue import DownloadTask, download_queue
from bot.services.storage import get_url, store_format, store_url
from bot.telegram_api.client import get_bot
from bot.utils.db import is_user_authorized
from bot.utils.exceptions import QueueFullError

# Create router for download handlers
download_router = Router()


def _create_format_keyboard(format_options: List[Tuple[str, str]], url_id: str) -> InlineKeyboardMarkup:
    """Create inline keyboard with format options."""
    keyboard = []
    row: List[InlineKeyboardButton] = []

    for i, (format_id, label) in enumerate(format_options):
        # Create a new row after every 2 buttons
        if i % 2 == 0 and row:
            keyboard.append(row)
            row = []

        # Use shorter callback data
        button = InlineKeyboardButton(text=label, callback_data=f"fmt:{format_id}:{url_id}")
        row.append(button)

    # Add the last row if it's not empty
    if row:
        keyboard.append(row)

    return InlineKeyboardMarkup(inline_keyboard=keyboard)


@download_router.message(F.text.startswith(("http://", "https://")))
async def process_url(message: Message) -> None:
    """
    Process URL message and show format options.

    Args:
        message: The message containing the URL
    """
    user_id = message.from_user.id
    url = message.text.strip()

    # Check if user is authorized
    if not await is_user_authorized(user_id):
        await message.answer(
            "⛔ <b>Access Denied</b>\n\n"
            "You don't have permission to use this bot.\n"
            "Please contact the administrator for access."
        )
        return

    logger.info(f"Received URL from user {user_id}: {url}")

    # Check if URL is from YouTube
    if is_youtube_url(url):
        await _handle_youtube_url(message, user_id, url)
    else:
        await message.answer("⚠️ <b>Unsupported URL</b>\n\nPlease provide a valid YouTube link.")


async def _handle_youtube_url(message: Message, user_id: int, url: str) -> None:
    """Handle YouTube URL processing."""
    # Store URL and get ID
    url_id = store_url(url)

    # Get available format options
    format_options = get_format_options()

    # Create inline keyboard with format options
    markup = _create_format_keyboard(format_options, url_id)

    await message.answer(
        "🎬 <b>Choose Download Format</b>\n\nSelect the format you want to download:",
        reply_markup=markup,
    )
    logger.info(f"Sent format selection keyboard to user {user_id}")


def _parse_callback_data(callback_data: str) -> tuple[str, str, str]:
    """Parse callback data and return cmd, format_id, url_id."""
    parts = callback_data.split(":")
    if len(parts) < 3:
        raise ValueError(f"Invalid format selection: parts length is {len(parts)}, expected at least 3")

    cmd = parts[0]
    url_id = parts[-1]
    format_id = ":".join(parts[1:-1])  # Reassemble format_id
    return cmd, format_id, url_id


def _build_status_message(format_data: FormatData, url: str, is_processing: bool, is_user_in_queue: bool) -> str:
    """Build status message for download."""
    # Header
    download_status = "queued" if is_processing else ""
    header = f"🔄 <b>Download {download_status}</b>"

    # Details
    details = f"Format: <b>{format_data['label']}</b>\nURL: {url}"

    # Queue info
    if is_processing:
        base_msg = "Your download has been added to the queue. "
        if is_user_in_queue:
            queue_msg = f"{base_msg}You already have downloads in the queue."
        else:
            queue_msg = f"{base_msg}You will be notified when processing begins."
    else:
        queue_msg = "Starting download now..."

    return f"{header}\n\n{details}\n\n{queue_msg}"


async def _validate_callback_data(callback: CallbackQuery) -> tuple[str, str, str] | None:
    """Validate callback data and return parsed values or None if invalid."""
    logger.debug(f"Received callback data: {callback.data}")

    if not callback.data:
        logger.error("Missing callback data")
        await callback.answer("Invalid callback data")
        return None

    try:
        cmd, format_id, url_id = _parse_callback_data(callback.data)
    except ValueError as e:
        logger.error(str(e))
        await callback.answer("Invalid format selection")
        return None

    logger.debug(f"Parsed values: cmd={cmd}, format_id={format_id}, url_id={url_id}")
    return cmd, format_id, url_id


async def _get_url_and_format(callback: CallbackQuery, format_id: str, url_id: str) -> Optional[Tuple[str, FormatData]]:
    """Get URL and format data, return None if not found."""
    # Get URL from storage
    url = get_url(url_id)
    if not url:
        logger.error(f"URL not found for ID: {url_id}")
        await callback.answer("URL not found or expired")
        return None

    # Get format details
    format_data = get_format_by_id(format_id)
    if not format_data:
        logger.error(f"Format not found: {format_id}")
        await callback.answer("Selected format not found")
        return None

    return url, format_data


@download_router.callback_query(F.data.startswith("fmt:"))
async def process_format_selection(callback: CallbackQuery) -> None:
    """
    Process format selection callback.

    Args:
        callback: Callback query containing format and URL ID
    """
    user_id = callback.from_user.id

    # Check if user is authorized
    if not await is_user_authorized(user_id):
        await callback.answer("⛔ Access Denied")
        return

    # Validate callback data
    parsed_data = await _validate_callback_data(callback)
    if not parsed_data:
        return

    cmd, format_id, url_id = parsed_data

    # Get URL and format data
    url_format_data = await _get_url_and_format(callback, format_id, url_id)
    if not url_format_data:
        return

    url, format_data = url_format_data
    logger.info(f"User {user_id} selected format: {format_data['label']} for URL: {url}")

    await _process_download_request(callback, format_data, format_id, url, url_id)


async def _process_download_request(
    callback: CallbackQuery, format_data: FormatData, format_id: str, url: str, url_id: str
) -> None:
    """Process the download request and add to queue."""

    # Store format selection and get bot
    store_format(url_id, format_id)
    bot = get_bot()

    # Acknowledge the callback
    await callback.answer(f"Processing your request in {format_data['label']} format...")

    try:
        # Check queue status
        is_processing = download_queue.is_processing
        is_user_in_queue = download_queue.is_user_in_queue(callback.message.chat.id)

        # Build and send status message
        status_text = _build_status_message(format_data, url, is_processing, is_user_in_queue)
        status_message = await callback.message.edit_text(status_text)

        # Create and add task to queue
        task = DownloadTask(
            chat_id=callback.message.chat.id,
            url=url,
            format_string=format_data["format"],
            status_message_id=status_message.message_id,
            additional_data={"bot": bot, "url_id": url_id},
        )
        queue_position = await download_queue.add_task(task)

        # Update message with queue position if needed
        if queue_position > 1:
            updated_status = f"{status_text}\n\nQueue position: {queue_position}"
            await bot.edit_message_text(
                updated_status,
                chat_id=callback.message.chat.id,
                message_id=status_message.message_id,
            )

        # Note: We don't clear the URL here since it will be done by the queue processor

    except QueueFullError as e:
        # Handle queue full error with user-friendly message
        context = getattr(e, "context", {})
        if "user_tasks" in context:
            error_message = (
                "❌ <b>Too Many Downloads</b>\n\n"
                f"You have reached the maximum of {context.get('limit', 5)} downloads in queue.\n"
                "Please wait for some downloads to complete before adding more."
            )
        else:
            error_message = (
                "❌ <b>Queue Full</b>\n\n"
                f"The download queue is currently full (maximum {context.get('limit', 50)} downloads).\n"
                "Please try again in a few minutes."
            )

        await callback.message.edit_text(error_message)
        logger.warning(
            f"Queue full error for user {callback.from_user.id}: {str(e)}",
            extra={"user_id": callback.from_user.id, **context},
        )
