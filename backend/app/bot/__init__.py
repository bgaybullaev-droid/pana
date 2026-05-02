"""Real Estate Seller Registration Bot.

A Telegram bot for seller registration with i18n support.
Supports Russian (ru) and Uzbek (uz) languages.
"""

from app.bot.analytics import check_rate_limit, track_event
from app.bot.i18n import SUPPORTED_LANGUAGES, get_language, load_translations, t
from app.bot.notifications import (
    get_bot_instance,
    notify_admins_new_registration,
    send_approval_notification,
    send_custom_notification,
    send_rejection_notification,
    set_bot_instance,
)

__all__ = [
    # i18n
    "t",
    "get_language",
    "load_translations",
    "SUPPORTED_LANGUAGES",
    # notifications
    "send_approval_notification",
    "send_rejection_notification",
    "send_custom_notification",
    "notify_admins_new_registration",
    "get_bot_instance",
    "set_bot_instance",
    # analytics
    "track_event",
    "check_rate_limit",
]
