"""Unified Telegram bot entry point with i18n support.

Supports Russian (ru) and Uzbek (uz) languages.
"""

import asyncio
import logging
import sys

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.exceptions import (
    TelegramBadRequest,
    TelegramForbiddenError,
    TelegramRetryAfter,
)
from aiogram.fsm.storage.redis import RedisStorage
from aiogram.types import ErrorEvent

from app.bot.handlers import router
from app.bot.i18n import load_translations
from app.bot.inline import inline_router
from app.bot.notifications import set_bot_instance
from app.bot.setup import set_bot_commands, set_menu_button
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


async def _on_telegram_error(event: ErrorEvent) -> bool:
    """Dispatcher-level catch-all so a Telegram API failure inside any
    handler (command, callback, or FSM step) never aborts long-polling.

    aiogram routes every unhandled handler exception here. We classify
    the common Telegram cases and log at an appropriate level, then
    return ``True`` to mark the update as handled — polling continues.

    * ``TelegramForbiddenError`` — user blocked the bot mid-flow.
      Expected, benign; INFO. Nothing else can be done for that chat.
    * ``TelegramRetryAfter`` — flood control. WARNING with the
      retry-after hint so ops can see throttling.
    * ``TelegramBadRequest`` — stale callback query, message too old,
      "message is not modified", etc. WARNING; usually a no-op race.
    * Anything else — a genuine bug. ERROR with full traceback.
    """
    exc = event.exception
    # ``update`` is best-effort context for the log line.
    upd_id = getattr(event.update, "update_id", "?")
    if isinstance(exc, TelegramForbiddenError):
        logger.info("bot.error.forbidden update=%s — user blocked the bot", upd_id)
    elif isinstance(exc, TelegramRetryAfter):
        logger.warning(
            "bot.error.flood update=%s retry_after=%ss", upd_id, exc.retry_after
        )
    elif isinstance(exc, TelegramBadRequest):
        logger.warning("bot.error.bad_request update=%s: %s", upd_id, exc)
    else:
        logger.exception("bot.error.unhandled update=%s: %s", upd_id, exc)
    return True


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

    # Dispatcher-level error handler — keeps polling alive when a
    # handler raises a Telegram API exception (bot blocked, flood
    # control, stale callback, …). See ``_on_telegram_error``.
    dp.errors.register(_on_telegram_error)

    # Set bot instance for notification service
    set_bot_instance(bot)

    return bot, dp


async def validate_integrations(bot: Bot) -> bool:
    """Startup health probe for the bot's critical integrations.

    Probes both dependencies and logs a clear health line for each so
    failures are visible in monitoring:

      * Telegram — the token is valid (``get_me`` succeeds). This is
        **fatal**: nothing works without it, so the function returns
        ``False`` and the caller aborts.
      * Redis — reachable; it backs the FSM storage. A dead Redis
        breaks multi-step flows (registration, profile edit) but the
        bot can still serve stateless commands (/help, /search). So a
        Redis failure is logged at ERROR but is **non-fatal** — the
        return value reflects Telegram health only.

    Returns ``True`` iff Telegram is healthy.
    """
    telegram_ok = True

    try:
        me = await bot.get_me()
        logger.info("Health: Telegram OK — bot=@%s id=%s", me.username, me.id)
    except Exception as exc:  # noqa: BLE001 — startup probe must catch all
        logger.error("Health: Telegram FAILED — invalid token or network: %s", exc)
        telegram_ok = False

    try:
        from app.db.redis import get_redis

        client = await get_redis()
        await client.ping()
        logger.info("Health: Redis OK — FSM storage reachable")
    except Exception as exc:  # noqa: BLE001
        logger.error(
            "Health: Redis FAILED (non-fatal) — FSM-backed flows "
            "(registration, profile edit) will not work; stateless "
            "commands still answer. Fix Redis and restart: %s",
            exc,
        )

    return telegram_ok


async def main():
    """Main entry point for the bot."""
    logger.info("Starting Real Estate Bot...")

    # Load translations
    load_translations()
    logger.info("Translations loaded")

    # Create bot and dispatcher
    bot, dp = create_bot()

    # Startup health probe. Telegram-token failure is fatal — abort so
    # the supervisor restarts us rather than spinning on a dead token.
    # Redis failure is logged loudly inside the probe but is non-fatal
    # (stateless commands still work), so it never blocks startup.
    if not await validate_integrations(bot):
        logger.error(
            "Telegram health check FAILED — invalid token. Aborting startup."
        )
        await bot.session.close()
        sys.exit(1)

    # Drop pending updates on startup
    await bot.delete_webhook(drop_pending_updates=True)

    # D1: configure the Menu Button. Idempotent; failure is non-fatal.
    await set_menu_button(bot)

    # Register the "/" command menu so the six commands autocomplete
    # in every Telegram client. Idempotent; failure is non-fatal.
    await set_bot_commands(bot)

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
