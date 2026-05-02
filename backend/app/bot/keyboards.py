"""Keyboards for seller registration bot with i18n support."""

from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
)

from app.bot.i18n import DEFAULT_LANGUAGE, t


def get_language_kb() -> InlineKeyboardMarkup:
    """Language selection keyboard (shown on first launch)."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🇷🇺 Русский", callback_data="lang_ru"),
                InlineKeyboardButton(text="🇺🇿 O'zbekcha", callback_data="lang_uz"),
            ],
        ]
    )


def get_start_kb(lang: str = DEFAULT_LANGUAGE) -> InlineKeyboardMarkup:
    """Start keyboard with register button."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=t(lang, "btn_register"), callback_data="register"
                )
            ],
        ]
    )


def get_cancel_kb(lang: str = DEFAULT_LANGUAGE) -> InlineKeyboardMarkup:
    """Cancel-only keyboard (for required fields like first_name)."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=t(lang, "btn_cancel"), callback_data="cancel")],
        ]
    )


def get_skip_kb(lang: str = DEFAULT_LANGUAGE) -> InlineKeyboardMarkup:
    """Skip + Back + Cancel keyboard for optional fields."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text=t(lang, "btn_back"), callback_data="back"),
                InlineKeyboardButton(text=t(lang, "btn_skip"), callback_data="skip"),
            ],
            [InlineKeyboardButton(text=t(lang, "btn_cancel"), callback_data="cancel")],
        ]
    )


def get_back_kb(lang: str = DEFAULT_LANGUAGE) -> InlineKeyboardMarkup:
    """Back + Cancel keyboard (for required fields after step 1)."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=t(lang, "btn_back"), callback_data="back")],
            [InlineKeyboardButton(text=t(lang, "btn_cancel"), callback_data="cancel")],
        ]
    )


def get_phone_kb(lang: str = DEFAULT_LANGUAGE) -> ReplyKeyboardMarkup:
    """Phone contact sharing keyboard."""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=t(lang, "btn_send_contact"), request_contact=True)],
        ],
        resize_keyboard=True,
        one_time_keyboard=True,
    )


def get_confirm_kb(lang: str = DEFAULT_LANGUAGE) -> InlineKeyboardMarkup:
    """Confirmation keyboard with edit/confirm/restart buttons."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=t(lang, "btn_confirm"), callback_data="confirm"
                ),
                InlineKeyboardButton(text=t(lang, "btn_edit"), callback_data="edit"),
            ],
            [
                InlineKeyboardButton(
                    text=t(lang, "btn_restart"), callback_data="restart"
                )
            ],
        ]
    )


def get_edit_fields_kb(lang: str = DEFAULT_LANGUAGE) -> InlineKeyboardMarkup:
    """Edit field selection keyboard."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=t(lang, "btn_edit_name"), callback_data="edit_first_name"
                ),
                InlineKeyboardButton(
                    text=t(lang, "btn_edit_lastname"), callback_data="edit_last_name"
                ),
            ],
            [
                InlineKeyboardButton(
                    text=t(lang, "btn_edit_phone"), callback_data="edit_phone"
                ),
                InlineKeyboardButton(
                    text=t(lang, "btn_edit_company"), callback_data="edit_company_name"
                ),
            ],
            [
                InlineKeyboardButton(
                    text=t(lang, "btn_edit_description"),
                    callback_data="edit_description",
                ),
                InlineKeyboardButton(
                    text=t(lang, "btn_edit_telegram"),
                    callback_data="edit_telegram_username",
                ),
            ],
            [
                InlineKeyboardButton(
                    text=t(lang, "btn_edit_instagram"),
                    callback_data="edit_instagram_url",
                ),
                InlineKeyboardButton(
                    text=t(lang, "btn_edit_website"), callback_data="edit_website_url"
                ),
            ],
            [
                InlineKeyboardButton(
                    text=t(lang, "btn_edit_email"), callback_data="edit_email"
                ),
                InlineKeyboardButton(
                    text=t(lang, "btn_edit_logo"), callback_data="edit_logo"
                ),
            ],
            [
                InlineKeyboardButton(
                    text=t(lang, "btn_back_to_summary"), callback_data="back_to_summary"
                )
            ],
        ]
    )


def get_rejected_kb(lang: str = DEFAULT_LANGUAGE) -> InlineKeyboardMarkup:
    """Keyboard for rejected users - re-apply option."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=t(lang, "btn_reapply"), callback_data="reapply"
                )
            ],
        ]
    )


def get_profile_kb(lang: str = DEFAULT_LANGUAGE) -> InlineKeyboardMarkup:
    """Profile view keyboard with edit and language options."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=t(lang, "btn_edit_profile"), callback_data="profile_edit"
                )
            ],
            [
                InlineKeyboardButton(
                    text=t(lang, "btn_change_language"),
                    callback_data="profile_language",
                )
            ],
        ]
    )


def get_profile_edit_kb(lang: str = DEFAULT_LANGUAGE) -> InlineKeyboardMarkup:
    """Profile edit field selection keyboard."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=t(lang, "btn_edit_company"), callback_data="pedit_company_name"
                ),
                InlineKeyboardButton(
                    text=t(lang, "btn_edit_description"),
                    callback_data="pedit_description",
                ),
            ],
            [
                InlineKeyboardButton(
                    text=t(lang, "btn_edit_telegram"),
                    callback_data="pedit_telegram_username",
                ),
                InlineKeyboardButton(
                    text=t(lang, "btn_edit_instagram"),
                    callback_data="pedit_instagram_url",
                ),
            ],
            [
                InlineKeyboardButton(
                    text=t(lang, "btn_edit_website"), callback_data="pedit_website_url"
                ),
                InlineKeyboardButton(
                    text=t(lang, "btn_edit_email"), callback_data="pedit_email"
                ),
            ],
            [
                InlineKeyboardButton(
                    text=t(lang, "btn_back"), callback_data="profile_back"
                )
            ],
        ]
    )


# Remove reply keyboard
remove_kb = ReplyKeyboardRemove()
