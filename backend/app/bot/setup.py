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
from aiogram.types import (
    BotCommand,
    BotCommandScopeDefault,
    MenuButtonDefault,
    MenuButtonWebApp,
    WebAppInfo,
)

from app.bot.i18n import t
from app.core.config import settings

logger = logging.getLogger(__name__)

# Per DECISION_MATRIX D1-Q1: a single neutral wordmark, since Telegram
# does not accept localised menu-button labels.
MENU_BUTTON_TEXT = "PANA"

# The six slash commands the bot answers, in the order they should
# appear in Telegram's "/" autocomplete menu. Each tuple is
# ``(command, i18n description key)``. The command names here MUST
# stay in sync with the ``@router.message(Command(...))`` decorators
# in ``handlers.py``.
_BOT_COMMANDS: tuple[tuple[str, str], ...] = (
    ("start", "cmd_desc_start"),
    ("search", "cmd_desc_search"),
    ("profile", "cmd_desc_profile"),
    ("language", "cmd_desc_language"),
    ("help", "cmd_desc_help"),
    ("cancel", "cmd_desc_cancel"),
)

# Telegram's ``set_my_commands`` localises by 2-letter client
# language_code. There is no script-variant code, so ``uz_cyrl`` users
# fall through to the ``uz`` (Latin) command list — the *in-bot* UI
# still honours uz_cyrl; only the "/" menu descriptions are Latin.
# ``None`` is the default scope shown to every other client locale.
_COMMAND_LOCALES: tuple[tuple[str | None, str], ...] = (
    (None, "ru"),  # default fallback for all unlisted client languages
    ("ru", "ru"),
    ("uz", "uz"),
)


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


async def set_bot_commands(bot: Bot) -> None:
    """Register the bot's slash-command list with Telegram.

    Without this call the six commands still *work* when typed, but
    don't appear in the client's "/" autocomplete menu — hurting
    discoverability. Idempotent: Telegram keeps only the latest list.

    Localised per ``_COMMAND_LOCALES``: a default scope plus ``ru`` and
    ``uz`` client-language scopes. Failure is logged, never fatal — the
    command menu is a UX nicety, not load-bearing.
    """
    for language_code, i18n_lang in _COMMAND_LOCALES:
        commands = [
            BotCommand(command=cmd, description=t(i18n_lang, desc_key))
            for cmd, desc_key in _BOT_COMMANDS
        ]
        try:
            await bot.set_my_commands(
                commands,
                scope=BotCommandScopeDefault(),
                language_code=language_code,
            )
        except TelegramAPIError as exc:
            logger.warning(
                "Failed to set bot commands (language_code=%s): %s",
                language_code,
                exc,
            )
    logger.info(
        "Bot commands registered: %s (locales: default, ru, uz)",
        ", ".join(f"/{c}" for c, _ in _BOT_COMMANDS),
    )
