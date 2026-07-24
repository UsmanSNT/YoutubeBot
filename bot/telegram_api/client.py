"""Telegram API client module for VideoGrabberBot."""

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from bot.config import TELEGRAM_TOKEN

# Initialize bot instance with default parse mode using new API
bot = Bot(
    token=TELEGRAM_TOKEN,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML),
)

# Initialize dispatcher
dp = Dispatcher()


def get_bot() -> Bot:
    """Get the bot instance."""
    return bot


def get_dispatcher() -> Dispatcher:
    """Get the dispatcher instance."""
    return dp
