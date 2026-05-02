"""Unified Telegram bot entry point with i18n support.

Supports Russian (ru) and Uzbek (uz) languages.
"""

import asyncio
import logging
import sys

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.fsm.storage.redis import RedisStorage

from app.bot.handlers import router
from app.bot.i18n import load_translations
from app.bot.notifications import set_bot_instance
from app.core.config import settings
from app.db.database import async_session_maker

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger(__name__)


class DbSessionMiddleware:
    """Middleware that injects an AsyncSession into each handler."""

    async def __call__(self, handler, event, data):
        async with async_session_maker() as session:
            data["session"] = session
            return await handler(event, data)


def create_bot() -> tuple[Bot, Dispatcher]:
    """Create and configure the Telegram bot and dispatcher."""
    token = settings.telegram_bot_token
    if not token:
        logger.error("TELEGRAM_BOT_TOKEN is not set!")
        sys.exit(1)

    bot = Bot(
        token=token,
        default=DefaultBotProperties(parse_mode="HTML"),
    )

    storage = RedisStorage.from_url(
        settings.redis_connection_url,
        state_ttl=86400,  # 24 hours — abandoned registrations auto-expire
        data_ttl=86400,
    )
    dp = Dispatcher(storage=storage)

    # Register DB session middleware for messages and callbacks
    dp.message.middleware(DbSessionMiddleware())
    dp.callback_query.middleware(DbSessionMiddleware())

    # Register handlers
    dp.include_router(router)

    # Set bot instance for notification service
    set_bot_instance(bot)

    return bot, dp


async def main():
    """Main entry point for the bot."""
    logger.info("Starting Real Estate Bot...")

    # Load translations
    load_translations()
    logger.info("Translations loaded")

    # Create bot and dispatcher
    bot, dp = create_bot()

    # Drop pending updates on startup
    await bot.delete_webhook(drop_pending_updates=True)

    logger.info("Bot is ready. Supported languages: Russian (ru), Uzbek (uz)")
    logger.info("Available commands: /start, /profile, /language, /help, /cancel")

    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
