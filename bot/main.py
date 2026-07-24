"""Main module for VideoGrabberBot."""

import asyncio

from aiogram import types
from loguru import logger

from bot.handlers.commands import router as commands_router
from bot.handlers.download import download_router
from bot.telegram_api.client import bot, dp
from bot.utils.db import init_db


async def startup() -> None:
    """Perform startup tasks."""
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
