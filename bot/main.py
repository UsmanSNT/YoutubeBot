"""Main module for VideoGrabberBot."""

import asyncio
import base64
import os

from aiogram import types
from loguru import logger

from bot.config import config
from bot.handlers.commands import router as commands_router
from bot.handlers.download import download_router
from bot.telegram_api.client import bot, dp
from bot.utils.db import init_db


def _write_cookies_from_env() -> None:
    """Write YouTube cookies.txt from the COOKIES_FILE_B64 env var, if set."""
    cookies_b64 = os.getenv("COOKIES_FILE_B64")
    if not cookies_b64:
        return

    config.COOKIES_FILE.write_bytes(base64.b64decode(cookies_b64))
    logger.info("Wrote cookies.txt from COOKIES_FILE_B64 environment variable")


async def startup() -> None:
    """Perform startup tasks."""
    _write_cookies_from_env()
    await init_db()

    await bot.set_my_commands([
        types.BotCommand(command="start", description="Start the bot"),
        types.BotCommand(command="help", description="Show help information"),
        types.BotCommand(command="invite", description="Generate invite link"),
        types.BotCommand(command="cancel", description="Cancel active downloads"),
    ])

    logger.info("Bot has been started successfully")


async def main() -> None:
    """Start the bot."""
    dp.include_router(commands_router)
    dp.include_router(download_router)

    await startup()

    logger.info("Starting bot polling...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
