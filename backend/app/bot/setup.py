"""One-shot bot configuration applied at process startup.

Block D D1 — Menu Button. Replaces the manual BotFather "set menu button"
step with an idempotent programmatic call so that production and dev
bots stay aligned automatically. Telegram accepts repeated identical
calls; only the most recent configuration is persisted server-side.

Failure modes (e.g. network blip at startup) are logged but never
abort the bot — the Menu Button is a UX nicety, not load-bearing.
"""

from __future__ import annotations

import logging

from aiogram import Bot
from aiogram.exceptions import TelegramAPIError
from aiogram.types import MenuButtonDefault, MenuButtonWebApp, WebAppInfo

from app.core.config import settings

logger = logging.getLogger(__name__)

# Per DECISION_MATRIX D1-Q1: a single neutral wordmark, since Telegram
# does not accept localised menu-button labels.
MENU_BUTTON_TEXT = "UcharMarket"


async def set_menu_button(bot: Bot) -> None:
    """Configure the bot's default chat menu button.

    If ``settings.telegram_webapp_url`` is empty (typical for local dev
    without a TWA host), the menu button is reset to the Telegram default
    rather than left in an inconsistent state from a previous run.

    In production (``settings.app_env == "production"``) an empty
    webapp URL is a misconfiguration — logged at WARNING so it
    surfaces on monitoring.
    """

    if not settings.telegram_webapp_url:
        if settings.app_env == "production":
            logger.warning(
                "TELEGRAM_WEBAPP_URL is empty in production — Menu Button "
                "is being reset to Telegram default. Set the env var to "
                "enable one-tap Mini App entry from the bot chat."
            )
        else:
            logger.info(
                "TELEGRAM_WEBAPP_URL is empty; resetting menu button to default"
            )
        try:
            await bot.set_chat_menu_button(menu_button=MenuButtonDefault())
        except TelegramAPIError as exc:
            logger.warning("Failed to reset chat menu button: %s", exc)
        return

    button = MenuButtonWebApp(
        text=MENU_BUTTON_TEXT,
        web_app=WebAppInfo(url=settings.telegram_webapp_url),
    )
    try:
        await bot.set_chat_menu_button(menu_button=button)
        logger.info(
            "Menu button configured: text=%r url=%s",
            MENU_BUTTON_TEXT,
            settings.telegram_webapp_url,
        )
    except TelegramAPIError as exc:
        logger.warning("Failed to set chat menu button: %s", exc)
