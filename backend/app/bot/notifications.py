"""Notification service for sending messages to users via Telegram bot.

This module provides functions to notify users about their application status
(approved/rejected) in their preferred language.
"""

import logging

from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError

from app.bot.i18n import DEFAULT_LANGUAGE, get_language, t

logger = logging.getLogger(__name__)


async def send_approval_notification(
    bot: Bot, telegram_id: int, language: str | None = None
) -> bool:
    """Send approval notification to a user.

    Args:
        bot: Telegram bot instance
        telegram_id: User's Telegram ID
        language: User's preferred language (defaults to Russian)

    Returns:
        True if notification was sent successfully, False otherwise
    """
    lang = get_language(language) if language else DEFAULT_LANGUAGE

    try:
        await bot.send_message(
            chat_id=telegram_id,
            text=f"🎉 {t(lang, 'notification_approved')}",
            parse_mode="HTML",
        )
        logger.info(f"Approval notification sent to user {telegram_id}")
        return True

    except TelegramForbiddenError:
        logger.warning(f"User {telegram_id} has blocked the bot")
        return False
    except TelegramBadRequest as e:
        logger.error(f"Failed to send approval notification to {telegram_id}: {e}")
        return False
    except Exception as e:
        logger.error(
            f"Unexpected error sending approval notification to {telegram_id}: {e}"
        )
        return False


async def send_rejection_notification(
    bot: Bot, telegram_id: int, reason: str | None = None, language: str | None = None
) -> bool:
    """Send rejection notification to a user.

    Args:
        bot: Telegram bot instance
        telegram_id: User's Telegram ID
        reason: Reason for rejection (optional)
        language: User's preferred language (defaults to Russian)

    Returns:
        True if notification was sent successfully, False otherwise
    """
    lang = get_language(language) if language else DEFAULT_LANGUAGE

    # Use a default reason if none provided
    if not reason:
        reason = t(lang, "rejection_reason_default")

    try:
        await bot.send_message(
            chat_id=telegram_id,
            text=t(lang, "notification_rejected", reason=reason),
            parse_mode="HTML",
        )
        logger.info(f"Rejection notification sent to user {telegram_id}")
        return True

    except TelegramForbiddenError:
        logger.warning(f"User {telegram_id} has blocked the bot")
        return False
    except TelegramBadRequest as e:
        logger.error(f"Failed to send rejection notification to {telegram_id}: {e}")
        return False
    except Exception as e:
        logger.error(
            f"Unexpected error sending rejection notification to {telegram_id}: {e}"
        )
        return False


async def send_custom_notification(
    bot: Bot, telegram_id: int, message: str, parse_mode: str = "HTML"
) -> bool:
    """Send a custom notification to a user.

    Args:
        bot: Telegram bot instance
        telegram_id: User's Telegram ID
        message: Message to send
        parse_mode: Parse mode for the message (HTML/Markdown)

    Returns:
        True if notification was sent successfully, False otherwise
    """
    try:
        await bot.send_message(
            chat_id=telegram_id,
            text=message,
            parse_mode=parse_mode,
        )
        logger.info(f"Custom notification sent to user {telegram_id}")
        return True

    except TelegramForbiddenError:
        logger.warning(f"User {telegram_id} has blocked the bot")
        return False
    except TelegramBadRequest as e:
        logger.error(f"Failed to send custom notification to {telegram_id}: {e}")
        return False
    except Exception as e:
        logger.error(
            f"Unexpected error sending custom notification to {telegram_id}: {e}"
        )
        return False


async def notify_admins_new_registration(
    bot: Bot,
    seller_data: dict,
    admin_chat_ids: list[int],
) -> int:
    """Notify admin chat(s) about a new seller registration.

    Returns count of successfully sent notifications.
    """
    message = (
        f"🆕 <b>Новая заявка продавца</b>\n\n"
        f"👤 Имя: {seller_data.get('first_name', '')} {seller_data.get('last_name', '') or ''}\n"
        f"📱 Телефон: {seller_data.get('phone', '')}\n"
        f"🏢 Компания: {seller_data.get('company_name') or '—'}\n"
        f"💬 Telegram: @{seller_data.get('telegram_username') or '—'}\n\n"
        f"📋 Проверьте в панели администратора."
    )
    sent = 0
    for chat_id in admin_chat_ids:
        try:
            await bot.send_message(chat_id=chat_id, text=message, parse_mode="HTML")
            sent += 1
            logger.info(f"Admin notification sent to chat {chat_id}")
        except Exception as e:
            logger.warning(f"Failed to notify admin chat {chat_id}: {e}")
    return sent


# Bot instance holder for use in API endpoints
_bot_instance: Bot | None = None


def set_bot_instance(bot: Bot) -> None:
    """Set the global bot instance for use in notifications."""
    global _bot_instance
    _bot_instance = bot
    logger.info("Bot instance set for notifications")


def get_bot_instance() -> Bot | None:
    """Get the global bot instance. Lazily creates one from config if not set."""
    global _bot_instance
    if _bot_instance is None:
        from app.core.config import settings

        token = settings.telegram_bot_token
        if token:
            _bot_instance = Bot(token=token)
            logger.info("Bot instance created lazily from config for API use")
    return _bot_instance
