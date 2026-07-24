#!/usr/bin/env python
"""Run script for VideoGrabberBot."""

import asyncio
import logging
import sys

from loguru import logger


def setup_logging():
    """Configure logger."""
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    logger.info("Starting VideoGrabberBot...")


async def start_bot():
    """Start the bot."""
    # Import here to avoid circular imports
    from bot.main import main

    await main()


if __name__ == "__main__":
    setup_logging()
    asyncio.run(start_bot())
