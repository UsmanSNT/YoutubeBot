"""Command handlers for VideoGrabberBot."""

from aiogram import Router
from aiogram.filters import Command, CommandStart
from aiogram.types import Message
from loguru import logger

from bot.config import ADMIN_USER_ID
from bot.utils.db import add_user, create_invite, is_user_authorized, use_invite

# Create router for command handlers
router = Router(name="commands_router")


@router.message(CommandStart())
async def command_start(message: Message) -> None:
    """
    Handle /start command.

    Display welcome message and bot instructions.
    Process invite codes if provided.
    """
    user_id = message.from_user.id
    username = message.from_user.username

    # Check if there's an invite code in the command
    args = message.text.split(maxsplit=1)
    invite_code = args[1] if len(args) > 1 else None

    # If there's an invite code, try to use it
    if invite_code:
        if await use_invite(invite_code, user_id):
            await message.answer(
                "🎉 <b>Welcome!</b>\n\n"
                "Your invite has been successfully activated! "
                "You now have access to VideoGrabberBot.\n\n"
                "I can help you download videos and audio from YouTube.\n\n"
                "<b>How to use:</b>\n"
                "1. Send me a YouTube link\n"
                "2. Choose the format you want to download\n"
                "3. Wait for the download to complete\n\n"
                "Use /help to see all available commands."
            )
            logger.info(f"User {user_id} (@{username}) successfully used invite: {invite_code}")
            return
        else:
            await message.answer(
                "❌ <b>Invalid Invite</b>\n\n"
                "This invite link is either invalid, expired, or has already been used.\n"
                "Please contact the administrator for a new invite."
            )
            logger.warning(f"User {user_id} (@{username}) tried invalid invite: {invite_code}")
            return

    # Check if user is authorized
    if not await is_user_authorized(user_id):
        await message.answer(
            "⚠️ <b>Access Restricted</b>\n\n"
            "You are not authorized to use this bot. Please contact the administrator "
            "or use an invite link to get access."
        )
        logger.info(f"Unauthorized access attempt: {user_id} (@{username})")
        return

    # User is authorized, provide welcome message
    await message.answer(
        "👋 <b>Welcome to VideoGrabberBot!</b>\n\n"
        "I can help you download videos and audio from YouTube.\n\n"
        "<b>How to use:</b>\n"
        "1. Send me a YouTube link\n"
        "2. Choose the format you want to download\n"
        "3. Wait for the download to complete\n\n"
        "Use /help to see all available commands."
    )
    logger.info(f"Start command from user: {user_id} (@{username})")


# bot/handlers/commands.py (help command implementation)


@router.message(Command("help"))
async def command_help(message: Message) -> None:
    """
    Handle /help command.

    Display all available commands and usage instructions.
    """
    user_id = message.from_user.id

    # Check if user is authorized
    if not await is_user_authorized(user_id):
        await message.answer("⚠️ <b>Access Restricted</b>\n\nYou are not authorized to use this bot.")
        return

    await message.answer(
        "📚 <b>VideoGrabberBot Help</b>\n\n"
        "<b>Available commands:</b>\n"
        "/start - Start the bot and see welcome message\n"
        "/help - Show this help message\n"
        "/invite - Generate an invite link (for authorized users)\n"
        "/adduser - Add a new user (admin only)\n"
        "/cancel - Cancel your active downloads\n\n"
        "<b>How to download:</b>\n"
        "Simply send a YouTube link, and I'll provide format options.\n\n"
        "<b>Supported formats:</b>\n"
        "• Video: SD (480p), HD (720p), Full HD (1080p), Original\n"
        "• Audio: MP3 (320kbps)\n\n"
        "<b>File size limit:</b> 2GB"
    )
    logger.info(f"Help command from user: {user_id}")


@router.message(Command("invite"))
async def command_invite(message: Message) -> None:
    """
    Handle /invite command.

    Generate a unique invite link that can be used once to get access to the bot.
    """
    user_id = message.from_user.id

    # Check if user is authorized
    if not await is_user_authorized(user_id):
        await message.answer("⚠️ <b>Access Restricted</b>\n\nYou are not authorized to use this bot.")
        return

    # Generate unique invite
    invite_code = await create_invite(user_id)

    if invite_code:
        bot_name = (await message.bot.get_me()).username
        invite_link = f"https://t.me/{bot_name}?start={invite_code}"

        await message.answer(
            "🔗 <b>Invite Link Generated</b>\n\n"
            f"<code>{invite_link}</code>\n\n"
            "This link can be used once to get access to the bot.\n"
            "⚠️ <b>Note:</b> Anyone with this link can use the bot, "
            "so share it only with people you trust."
        )
        logger.info(f"Invite created by user: {user_id}, code: {invite_code}")
    else:
        await message.answer("❌ <b>Error</b>\n\nCould not generate invite link. Please try again later.")
        logger.error(f"Failed to create invite for user: {user_id}")


@router.message(Command("adduser"))
async def command_adduser(message: Message) -> None:
    """
    Handle /adduser command.

    Add a new user to the authorized users list (admin only).
    Usage: /adduser username or user_id
    """
    user_id = message.from_user.id

    # Check if user is admin
    if user_id != ADMIN_USER_ID:
        await message.answer("⚠️ <b>Admin Only</b>\n\nThis command is only available to the bot administrator.")
        logger.warning(f"Admin command attempt by non-admin: {user_id}")
        return

    # Get command arguments
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.answer(
            "⚠️ <b>Usage Error</b>\n\n"
            "Please provide a username or user ID.\n"
            "Example: <code>/adduser username</code> or <code>/adduser 123456789</code>"
        )
        return

    target = args[1].strip()

    # Check if target is a numeric user ID
    if target.isdigit():
        target_id = int(target)
        user_added = await add_user(target_id, added_by=user_id)

        if user_added:
            await message.answer(
                "✅ <b>User Added</b>\n\n"
                f"User with ID <code>{target_id}</code> has been added to the authorized users list."
            )
            logger.info(f"Admin added user by ID: {target_id}")
        else:
            await message.answer(
                "ℹ️ <b>User Already Exists</b>\n\n"
                f"User with ID <code>{target_id}</code> is already in the authorized users list."
            )
    else:
        # Target is a username (handle both with and without @ prefix)
        username = target.lstrip("@")

        await message.answer(
            "ℹ️ <b>User Cannot Be Added Directly by Username</b>\n\n"
            f"Due to Telegram API limitations, the user <b>@{username}</b> needs to start a chat "
            "with the bot first. Then, they can be authorized using their user ID.\n\n"
            "Please ask the user to send a message to the bot first, then use their user ID."
        )
        logger.info(f"Admin attempted to add user by username: @{username}")


# bot/handlers/commands.py (cancel command implementation)


@router.message(Command("cancel"))
async def command_cancel(message: Message) -> None:
    """
    Handle /cancel command.

    Cancel all download tasks for the user in the queue.
    """
    user_id = message.from_user.id

    # Check if user is authorized
    if not await is_user_authorized(user_id):
        await message.answer("⚠️ <b>Access Restricted</b>\n\nYou are not authorized to use this bot.")
        return

    # Import here to avoid circular imports
    from bot.services.queue import download_queue

    # Check if user has tasks in queue
    if not download_queue.is_user_in_queue(message.chat.id):
        await message.answer("ℹ️ <b>No Active Downloads</b>\n\nYou don't have any downloads in the queue to cancel.")
        return

    # Clear user tasks
    removed = await download_queue.clear_user_tasks(message.chat.id)

    download_word = "download" if removed == 1 else "downloads"
    await message.answer(
        f"✅ <b>Downloads Cancelled</b>\n\nSuccessfully cancelled {removed} {download_word} from the queue."
    )
    logger.info(f"User {user_id} cancelled {removed} downloads")
