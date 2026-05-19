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
from app.bot.inline import inline_router
from app.bot.notifications import set_bot_instance
from app.bot.setup import set_menu_button
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
    # Block D D5 — Inline Mode handler. Register *after* the main
    # router so command/state-bound dispatch retains priority on
    # message events; inline_query events are routed independently.
    dp.include_router(inline_router)

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

    # D1: configure the Menu Button. Idempotent; failure is non-fatal.
    await set_menu_button(bot)

    logger.info(
        "Bot is ready. Supported languages: Russian (ru), "
        "Uzbek Latin (uz), Uzbek Cyrillic (uz_cyrl)"
    )
    logger.info(
        "Available commands: /start, /profile, /language, /help, /cancel, /search"
    )
    # Block D D5 — Inline Mode must be enabled in BotFather:
    #   /setinline @<bot> → placeholder "Район, комнаты, цена"
    # The registration above is necessary but not sufficient; the
    # BotFather flag is also required for ``@<bot> <q>`` to surface.
    logger.info("Inline Mode handler registered (BotFather flag also required).")
    # Block D D4 — surface the subscription gate mode at startup so
    # ops sees which policy is active.
    if settings.cabinet_subscription_open_to_all:
        logger.info(
            "Cabinet subscription: PHASE-1 (open to all sellers). "
            "Flip CABINET_SUBSCRIPTION_OPEN_TO_ALL=false to enforce."
        )
    else:
        logger.info(
            "Cabinet subscription: ENFORCED (paid-only). "
            "Sellers without an active CABINET subscription cannot use D4 autopost."
        )
    # Block D D1 — surface the uz_cyrl fallback safety switch state.
    if settings.i18n_uz_cyrl_bot_fallback_to_ru:
        logger.warning(
            "uz_cyrl bot translations are temporarily falling back to ru "
            "(I18N_UZ_CYRL_BOT_FALLBACK_TO_RU=true). Disable once native "
            "review of uz_cyrl.json completes."
        )

    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
